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
pub async fn cancel_job(job_id: String, state: State<'_, AppSidecarState>) -> Result<Value, String> {
    let mut manager = state.lock().await;
    match manager.send_request("cancel", serde_json::json!({ "job_id": job_id })).await {
        Ok(resp) => Ok(resp.data.unwrap_or(serde_json::json!({}))),
        Err(e) => Err(format!("Cancel error: {}", e)),
    }
}
