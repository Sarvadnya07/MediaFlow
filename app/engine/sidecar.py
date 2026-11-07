import json
import os
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.protocol import IPCRequest, IPCResponse, ProgressEvent
from app.engine.queue_manager import DownloadQueueManager
from app.services import yt_service, ffmpeg_service
from app.services.yt_service import DownloadCancelledError
from app.security import SecurityError
from app.config import settings
from app.logging_config import logger


class SidecarRunner:
    def __init__(self, stdin=sys.stdin, stdout=sys.stdout):
        self.stdin = stdin
        self.stdout = stdout
        self.running = True
        self._stdout_lock = threading.Lock()
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.jobs_lock = threading.Lock()

        # Integrated persistent queue manager
        def on_queue_event(evt):
            self.send_event(evt.get("data", {}).get("job_id", "queue"), evt.get("event", "queue"), evt.get("data", {}))

        self.queue_mgr = DownloadQueueManager(event_callback=on_queue_event)

    def send_line(self, obj: Dict[str, Any]):
        """Safely write single JSON line followed by newline and flush immediately."""
        raw = json.dumps(obj) + "\n"
        with self._stdout_lock:
            self.stdout.write(raw)
            self.stdout.flush()

    def send_response(self, req_id: str, status: str = "success", data: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None):
        resp = IPCResponse(id=req_id, type="response", status=status, data=data, error=error)
        self.send_line(resp.model_dump())

    def send_event(self, job_id: str, event_name: str, data: Dict[str, Any]):
        evt = ProgressEvent(id=job_id, type="event", event=event_name, data=data)
        self.send_line(evt.model_dump())

    def run(self):
        """Main stdio loop reading line-by-line requests from Rust Tauri host."""
        sys.stderr.write("[MediaDock Sidecar] Started JSONL listener on stdio.\n")
        sys.stderr.flush()

        while self.running:
            try:
                line = self.stdin.readline()
                if not line:
                    # EOF reached - parent process closed stdin pipe
                    break

                line_str = line.strip()
                if not line_str:
                    continue

                self.handle_raw_message(line_str)
            except Exception as e:
                sys.stderr.write(f"[MediaDock Sidecar ERROR] Unhandled loop exception: {str(e)}\n")
                sys.stderr.flush()

        sys.stderr.write("[MediaDock Sidecar] Shutting down cleanly.\n")
        sys.stderr.flush()

    def handle_raw_message(self, raw_line: str):
        try:
            parsed = json.loads(raw_line)
        except Exception as e:
            self.send_response(
                req_id="unknown",
                status="error",
                error={"code": "INVALID_JSON", "message": f"Malformed JSON: {str(e)}"}
            )
            return

        try:
            req = IPCRequest.model_validate(parsed)
        except Exception as e:
            req_id = str(parsed.get("id", "unknown")) if isinstance(parsed, dict) else "unknown"
            self.send_response(
                req_id=req_id,
                status="error",
                error={"code": "VALIDATION_ERROR", "message": f"Invalid IPC request schema: {str(e)}"}
            )
            return

        self.dispatch_action(req)

    def dispatch_action(self, req: IPCRequest):
        action = req.action
        payload = req.payload
        req_id = req.id

        try:
            if action == "initialize":
                self.send_response(req_id, status="success", data={"version": "1.0.0", "status": "ready"})

            elif action == "shutdown":
                self.running = False
                self.queue_mgr.shutdown()
                self.send_response(req_id, status="success", data={"message": "Shutting down."})

            elif action == "health_check":
                ffmpeg_ok = False
                try:
                    ffmpeg_service.resolve_ffmpeg_path()
                    ffmpeg_ok = True
                except Exception:
                    ffmpeg_ok = False

                self.send_response(req_id, status="success", data={
                    "status": "healthy" if ffmpeg_ok else "degraded",
                    "dependencies": {
                        "yt_dlp": True,
                        "ffmpeg": ffmpeg_ok,
                    }
                })

            elif action == "get_capabilities":
                ffmpeg_caps = ffmpeg_service.get_ffmpeg_capabilities()
                self.send_response(req_id, status="success", data={
                    "supported_actions": [
                        "initialize", "health_check", "analyze", "get_formats",
                        "download", "cancel", "queue_add", "queue_list", "queue_cancel",
                        "queue_retry", "queue_remove", "verify", "convert", "get_capabilities", "shutdown"
                    ],
                    "video_formats": ["mp4", "mkv", "webm"],
                    "audio_formats": ffmpeg_caps.get("supported_audio_formats", ["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus"]),
                    "ffmpeg": ffmpeg_caps,
                })

            elif action in ("analyze", "get_formats"):
                url = payload.get("url")
                if not url:
                    self.send_response(req_id, status="error", error={"code": "MISSING_ARGUMENT", "message": "Missing 'url' parameter."})
                    return

                allow_private = payload.get("allow_private", False)
                analysis = yt_service.analyze_url(url, allow_private=allow_private)
                self.send_response(req_id, status="success", data=analysis.model_dump())

            elif action == "cancel":
                job_id = payload.get("job_id")
                if not job_id:
                    self.send_response(req_id, status="error", error={"code": "MISSING_ARGUMENT", "message": "Missing 'job_id'."})
                    return

                cancelled = yt_service.trigger_cancellation(job_id)
                self.send_response(req_id, status="success", data={"job_id": job_id, "cancelled": cancelled})

            elif action == "download":
                job_id = payload.get("job_id") or req_id
                url = payload.get("url")
                output_dir = payload.get("output_dir") or str(settings.DOWNLOADS_DIR)
                format_id = payload.get("format_id")
                quality = payload.get("quality")
                subtitle_lang = payload.get("subtitle_lang")
                ffmpeg_location = payload.get("ffmpeg_location")
                allow_private = payload.get("allow_private", False)

                if not url:
                    self.send_response(req_id, status="error", error={"code": "MISSING_ARGUMENT", "message": "Missing 'url'."})
                    return

                # Spawn download thread
                def _do_download():
                    try:
                        def on_progress(p_data):
                            self.send_event(job_id, "progress", p_data)

                        result = yt_service.download_stream(
                            url=url,
                            output_dir=output_dir,
                            job_id=job_id,
                            format_id=format_id,
                            quality=quality,
                            subtitle_lang=subtitle_lang,
                            progress_callback=on_progress,
                            ffmpeg_location=ffmpeg_location,
                            allow_private=allow_private
                        )
                        self.send_response(req_id, status="success", data=result)
                    except DownloadCancelledError:
                        self.send_response(req_id, status="cancelled", data={"job_id": job_id, "message": "Download cancelled by user."})
                    except Exception as e:
                        sys.stderr.write(f"[Download Worker Error] {traceback.format_exc()}\n")
                        sys.stderr.flush()
                        self.send_response(req_id, status="error", error={"code": "DOWNLOAD_FAILED", "message": str(e)})
                    finally:
                        with self.jobs_lock:
                            self.active_jobs.pop(job_id, None)

                t = threading.Thread(target=_do_download, name=f"download-{job_id}", daemon=True)
                with self.jobs_lock:
                    self.active_jobs[job_id] = t
                t.start()

            elif action == "queue_add":
                url = payload.get("url")
                if not url:
                    self.send_response(req_id, status="error", error={"code": "MISSING_ARGUMENT", "message": "Missing 'url'."})
                    return

                item = self.queue_mgr.add_job(
                    url=url,
                    title=payload.get("title"),
                    format_id=payload.get("format_id"),
                    quality=payload.get("quality"),
                    subtitle_lang=payload.get("subtitle_lang"),
                    output_dir=payload.get("output_dir"),
                    playlist_id=payload.get("playlist_id"),
                    playlist_index=payload.get("playlist_index"),
                )
                self.send_response(req_id, status="success", data=item.model_dump())

            elif action == "queue_list":
                jobs = self.queue_mgr.get_all_jobs()
                self.send_response(req_id, status="success", data={"jobs": [j.model_dump() for j in jobs]})

            elif action == "queue_cancel":
                job_id = payload.get("job_id")
                cancelled = self.queue_mgr.cancel_job(job_id)
                self.send_response(req_id, status="success", data={"job_id": job_id, "cancelled": cancelled})

            elif action == "queue_retry":
                job_id = payload.get("job_id")
                retried = self.queue_mgr.retry_job(job_id)
                self.send_response(req_id, status="success", data={"job_id": job_id, "retried": retried})

            elif action == "queue_remove":
                job_id = payload.get("job_id")
                removed = self.queue_mgr.remove_job(job_id)
                self.send_response(req_id, status="success", data={"job_id": job_id, "removed": removed})

            elif action == "verify":
                file_path = payload.get("file_path")
                if not file_path:
                    self.send_response(req_id, status="error", error={"code": "MISSING_ARGUMENT", "message": "Missing 'file_path'."})
                    return

                res = ffmpeg_service.verify_media_file(file_path)
                self.send_response(req_id, status="success", data=res)

            elif action == "convert":
                input_file = payload.get("input_file")
                output_format = payload.get("output_format", "mp3")
                bitrate = payload.get("bitrate", "192k")
                ffmpeg_bin = payload.get("ffmpeg_bin")

                if not input_file:
                    self.send_response(req_id, status="error", error={"code": "MISSING_ARGUMENT", "message": "Missing 'input_file'."})
                    return

                out_file = ffmpeg_service.convert_to_audio(
                    input_file=input_file,
                    output_format=output_format,
                    bitrate=bitrate,
                    ffmpeg_bin=ffmpeg_bin
                )
                self.send_response(req_id, status="success", data={"output_file": out_file})

            else:
                self.send_response(req_id, status="error", error={"code": "UNKNOWN_ACTION", "message": f"Action '{action}' is not supported."})

        except SecurityError as sec_err:
            self.send_response(req_id, status="error", error={"code": "SECURITY_VIOLATION", "message": str(sec_err)})
        except Exception as e:
            sys.stderr.write(f"[Sidecar Dispatch Error] {traceback.format_exc()}\n")
            sys.stderr.flush()
            self.send_response(req_id, status="error", error={"code": "INTERNAL_ERROR", "message": str(e)})


def main():
    runner = SidecarRunner()
    runner.run()


if __name__ == "__main__":
    main()
