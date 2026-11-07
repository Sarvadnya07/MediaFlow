"""
MediaDock Native Sidecar Entrypoint.
Invoked by Tauri host in packaged binary distributions.
"""
from app.engine.sidecar import SidecarRunner


def main():
    runner = SidecarRunner()
    runner.run()


if __name__ == "__main__":
    main()
