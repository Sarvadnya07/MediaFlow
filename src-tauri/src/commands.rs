use crate::sidecar::SidecarManager;
use serde_json::Value;
use std::sync::Arc;
use tauri::State;
use tokio::sync::Mutex;

pub type AppSidecarState = Arc<Mutex<SidecarManager>>;

#[tauri::command]
pub async fn check_health(state: State<'_, AppSidecarState>) -> Result<Value, String> {
    let mut manager = state.lock().await;
    match manager.send_request("health_check", serde_json::json!({})).await {
        Ok(resp) => {
            if resp.status == "success" {
                Ok(resp.data.unwrap_or(serde_json::json!({})))
            } else {
                Err(format!("Health check error: {:?}", resp.error))
            }
        }
        Err(e) => Err(format!("Sidecar communication error: {}", e)),
    }
}

#[tauri::command]
pub async fn get_capabilities(state: State<'_, AppSidecarState>) -> Result<Value, String> {
    let mut manager = state.lock().await;
    match manager.send_request("get_capabilities", serde_json::json!({})).await {
        Ok(resp) => {
            if resp.status == "success" {
                Ok(resp.data.unwrap_or(serde_json::json!({})))
            } else {
                Err(format!("Error: {:?}", resp.error))
            }
        }
        Err(e) => Err(format!("Sidecar communication error: {}", e)),
    }
}

#[tauri::command]
pub async fn analyze_url(url: String, state: State<'_, AppSidecarState>) -> Result<Value, String> {
    let mut manager = state.lock().await;
    match manager.send_request("analyze", serde_json::json!({ "url": url })).await {
        Ok(resp) => {
            if resp.status == "success" {
                Ok(resp.data.unwrap_or(serde_json::json!({})))
            } else {
                Err(format!("Analysis error: {:?}", resp.error))
            }
        }
        Err(e) => Err(format!("Sidecar communication error: {}", e)),
    }
}

#[tauri::command]
pub async fn start_download(
    url: String,
    format_id: Option<String>,
    quality: Option<String>,
    subtitle_lang: Option<String>,
    output_dir: Option<String>,
    state: State<'_, AppSidecarState>,
) -> Result<Value, String> {
    let mut manager = state.lock().await;
    let job_id = uuid::Uuid::new_v4().to_string();

    let mut payload = serde_json::json!({
        "job_id": job_id,
        "url": url,
    });

    if let Some(fid) = format_id {
        payload["format_id"] = serde_json::json!(fid);
    }
    if let Some(q) = quality {
        payload["quality"] = serde_json::json!(q);
    }
    if let Some(sub) = subtitle_lang {
        payload["subtitle_lang"] = serde_json::json!(sub);
    }
    if let Some(dir) = output_dir {
        payload["output_dir"] = serde_json::json!(dir);
    }

    match manager.send_request("download", payload).await {
        Ok(resp) => {
            if resp.status == "success" {
                Ok(resp.data.unwrap_or(serde_json::json!({})))
            } else if resp.status == "cancelled" {
                Err("Download was cancelled.".to_string())
            } else {
                Err(format!("Download failed: {:?}", resp.error))
            }
        }
        Err(e) => Err(format!("Download communication error: {}", e)),
    }
}

#[tauri::command]
pub async fn cancel_job(job_id: String, state: State<'_, AppSidecarState>) -> Result<Value, String> {
    let mut manager = state.lock().await;
    match manager.send_request("cancel", serde_json::json!({ "job_id": job_id })).await {
        Ok(resp) => Ok(resp.data.unwrap_or(serde_json::json!({}))),
        Err(e) => Err(format!("Cancel error: {}", e)),
    }
}
