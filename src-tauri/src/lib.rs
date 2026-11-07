pub mod commands;
pub mod sidecar;

use commands::{
    analyze_url, cancel_job, check_health, get_capabilities, queue_add, queue_list, queue_remove,
    queue_retry, start_download, AppSidecarState,
};
use sidecar::SidecarManager;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let app_handle = app.handle().clone();
            let mut sidecar_mgr = SidecarManager::new(app_handle);

            // Attempt initial sidecar startup
            if let Err(e) = sidecar_mgr.start() {
                eprintln!("[MediaDock WARNING] Sidecar delayed startup: {}", e);
            }

            let state: AppSidecarState = Arc::new(Mutex::new(sidecar_mgr));
            app.manage(state);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            check_health,
            get_capabilities,
            analyze_url,
            start_download,
            cancel_job,
            queue_add,
            queue_list,
            queue_retry,
            queue_remove
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
