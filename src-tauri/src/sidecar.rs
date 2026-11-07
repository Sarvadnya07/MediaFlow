use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Emitter};
use thiserror::Error;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum SidecarError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("Process not running")]
    NotRunning,
    #[error("Request timed out: {0}")]
    Timeout(String),
    #[error("Sidecar returned error: {code}: {message}")]
    ProtocolError { code: String, message: String },
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IPCRequest {
    pub id: String,
    pub action: String,
    pub payload: Value,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct IPCResponse {
    pub id: String,
    #[serde(rename = "type")]
    pub msg_type: String,
    pub status: String,
    pub data: Option<Value>,
    pub error: Option<Value>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ProgressEvent {
    pub id: String,
    #[serde(rename = "type")]
    pub msg_type: String,
    pub event: String,
    pub data: Value,
}

pub struct SidecarManager {
    stdin: Option<ChildStdin>,
    pending_requests: Arc<Mutex<HashMap<String, tokio::sync::oneshot::Sender<IPCResponse>>>>,
    child: Option<Child>,
    app_handle: AppHandle,
}

impl SidecarManager {
    pub fn new(app_handle: AppHandle) -> Self {
        Self {
            stdin: None,
            pending_requests: Arc::new(Mutex::new(HashMap::new())),
            child: None,
            app_handle,
        }
    }

    pub fn start(&mut self) -> Result<(), SidecarError> {
        if self.child.is_some() {
            return Ok(());
        }

        // Locate Python executable (check virtual environment first, then python on PATH)
        let python_cmd = "python";
        let venv_python = std::path::Path::new("../venv/Scripts/python.exe");
        let venv_python_abs = std::path::Path::new("venv/Scripts/python.exe");

        let resolved_python = if venv_python.exists() {
            venv_python.to_str().unwrap()
        } else if venv_python_abs.exists() {
            venv_python_abs.to_str().unwrap()
        } else {
            python_cmd
        };

        eprintln!("[Rust Sidecar] Spawning Python worker: {}", resolved_python);

        let mut process = Command::new(resolved_python)
            .args(&["-m", "app.engine.sidecar"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()?;

        let stdin = process.stdin.take().ok_or(SidecarError::NotRunning)?;
        let stdout = process.stdout.take().ok_or(SidecarError::NotRunning)?;

        self.stdin = Some(stdin);
        self.child = Some(process);

        // Spawn async stdout reader thread
        let pending = Arc::clone(&self.pending_requests);
        let app_handle_clone = self.app_handle.clone();

        std::thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line_res in reader.lines() {
                match line_res {
                    Ok(line) => {
                        let trimmed = line.trim();
                        if trimmed.is_empty() {
                            continue;
                        }

                        // Parse as generic JSON object first
                        if let Ok(val) = serde_json::from_str::<Value>(trimmed) {
                            let msg_type = val.get("type").and_then(|v| v.as_str()).unwrap_or("response");

                            if msg_type == "event" {
                                // Forward progress event to frontend via Tauri Event Bus
                                if let Ok(event_obj) = serde_json::from_value::<ProgressEvent>(val) {
                                    let _ = app_handle_clone.emit("sidecar-event", &event_obj);
                                }
                            } else {
                                // Correlate response to pending request ID
                                if let Ok(resp) = serde_json::from_value::<IPCResponse>(val) {
                                    let mut lock = pending.lock().unwrap();
                                    if let Some(tx) = lock.remove(&resp.id) {
                                        let _ = tx.send(resp);
                                    }
                                }
                            }
                        }
                    }
                    Err(err) => {
                        eprintln!("[Rust Sidecar Stdout Reader ERROR] {}", err);
                        break;
                    }
                }
            }
            eprintln!("[Rust Sidecar Stdout Reader] Exited.");
        });

        Ok(())
    }

    pub async fn send_request(
        &mut self,
        action: &str,
        payload: Value,
    ) -> Result<IPCResponse, SidecarError> {
        if self.stdin.is_none() {
            self.start()?;
        }

        let req_id = Uuid::new_v4().to_string();
        let request = IPCRequest {
            id: req_id.clone(),
            action: action.to_string(),
            payload,
        };

        let json_line = serde_json::to_string(&request)? + "\n";

        // Setup correlation oneshot channel
        let (tx, rx) = tokio::sync::oneshot::channel();
        {
            let mut lock = self.pending_requests.lock().unwrap();
            lock.insert(req_id.clone(), tx);
        }

        // Write to child stdin
        if let Some(ref mut stdin) = self.stdin {
            stdin.write_all(json_line.as_bytes())?;
            stdin.flush()?;
        } else {
            return Err(SidecarError::NotRunning);
        }

        // Await correlated response with timeout
        match tokio::time::timeout(Duration::from_secs(60), rx).await {
            Ok(Ok(response)) => Ok(response),
            Ok(Err(_)) => Err(SidecarError::NotRunning),
            Err(_) => {
                let mut lock = self.pending_requests.lock().unwrap();
                lock.remove(&req_id);
                Err(SidecarError::Timeout(req_id))
            }
        }
    }

    pub fn shutdown(&mut self) {
        if let Some(mut stdin) = self.stdin.take() {
            let shutdown_cmd = serde_json::json!({
                "id": Uuid::new_v4().to_string(),
                "action": "shutdown",
                "payload": {}
            });
            let _ = writeln!(stdin, "{}", shutdown_cmd);
            let _ = stdin.flush();
        }

        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_ipc_request_serialization() {
        let req = IPCRequest {
            id: "req-123".to_string(),
            action: "health_check".to_string(),
            payload: json!({}),
        };

        let serialized = serde_json::to_string(&req).expect("Failed to serialize");
        assert!(serialized.contains("req-123"));
        assert!(serialized.contains("health_check"));
    }

    #[test]
    fn test_ipc_response_deserialization() {
        let raw = r#"{"id":"res-1","type":"response","status":"success","data":{"version":"1.0.0"},"error":null}"#;
        let resp: IPCResponse = serde_json::from_str(raw).expect("Failed to deserialize");
        assert_eq!(resp.id, "res-1");
        assert_eq!(resp.status, "success");
        assert_eq!(resp.msg_type, "response");
        assert_eq!(resp.data.unwrap()["version"], "1.0.0");
    }

    #[test]
    fn test_progress_event_deserialization() {
        let raw = r#"{"id":"job-456","type":"event","event":"progress","data":{"percent":55.5,"speed":1024}}"#;
        let evt: ProgressEvent = serde_json::from_str(raw).expect("Failed to deserialize event");
        assert_eq!(evt.id, "job-456");
        assert_eq!(evt.msg_type, "event");
        assert_eq!(evt.event, "progress");
        assert_eq!(evt.data["percent"], 55.5);
    }
}
