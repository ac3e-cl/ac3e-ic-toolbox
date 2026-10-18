# Opening a terminal with Docker Desktop Play

When the container starts without a command and `DISPLAY` is nonempty, the
entrypoint opens `xterm` with an interactive Bash shell. The image's `.bashrc`
loads the EDA environment, PDK selection and aliases. `xterm` stays in the
foreground: closing the terminal stops the container; Play starts it again and
opens a new terminal. No attached stdin or Docker TTY is required.

This is an external X11 window, **not** Docker Desktop's integrated Terminal/Exec
tab. An image entrypoint cannot open a Docker Desktop tab on the host.

## Configure the container once

Build or pull the updated image, then **create a new container** with the required
X11 configuration. Play restarts an existing container with its original image,
command, environment and mounts; it does not apply an updated tag automatically.
Preserve design volumes when replacing a container.

- Keep the image's `/entrypoint.sh` entrypoint. Leave the container command empty
  for automatic X11 selection, or set it to `--x11`. Do not set it to `bash` or
  `--shell`: explicit commands and shell mode intentionally do not open windows.
- Set `DISPLAY` to a server reachable **from the container**, not merely from a
  host shell. Its value is preserved as supplied; no OS-specific address is
  guessed by the image.
- Provide X11 authorization. If using an Xauthority file, mount the matching
  file read-only, set `XAUTHORITY` to its container path, and ensure the container
  user can read it. TCP connections need a matching cookie/address entry too.
- Mount the design directory at `/home/designer/shared`.
- Do not use automatic container removal (`--rm`) if Play must restart it later.

Once created, the host X server must be running whenever Play is pressed.
An unreachable or unauthorized server produces an `xterm` error in container
logs and the container exits, rather than staying running without a terminal.

## Host-specific X11 connection

| Host | X server and container connection |
| --- | --- |
| Linux, native Docker Engine | Use the host's X server (or XWayland). Pass its `DISPLAY`, bind `/tmp/.X11-unix` read-only, and supply Xauthority. This also requires an X server on Wayland sessions. |
| Linux, Docker Desktop | The daemon is in a VM: do not assume the host's Unix X socket is usable through a file-sharing mount. Use a deliberately configured TCP X11 endpoint reachable through `host.docker.internal:<display>`, with authorization and firewall restrictions, or use the VNC alternative below. |
| macOS, Docker Desktop | Start XQuartz and enable **Allow connections from network clients**, then restart XQuartz. For XQuartz display 0, set container `DISPLAY=host.docker.internal:0`. Supply authorization for this TCP connection. Do not pass the macOS launchd socket path as the container display or mount Linux X11 socket paths. |
| Windows + WSL 2, Docker Desktop, WSLg | With Docker Desktop WSL integration enabled, a working WSLg installation may expose `/tmp/.X11-unix` inside the WSL distribution. Create the container from that distribution, pass its `DISPLAY`, and bind the actual socket directory. Confirm that the Docker daemon can access this bind mount; a socket visible in WSL alone does not guarantee access from the Desktop VM. |
| Windows + WSL 2, Docker Desktop, VcXsrv | Start VcXsrv on Windows with TCP listening enabled. For display 0, use `DISPLAY=host.docker.internal:0` when that address reaches the Windows server. Otherwise use the Windows host address reachable from the container; do not guess it from a WSL address or use `localhost`. Configure server authorization and Windows Firewall for the container/WSL network. A Linux X11 socket bind is not needed for this TCP route. |

For TCP display 0, the X11 port is 6000 (6000 plus the display number for other
displays). Limit access to the required Docker/WSL network. Do **not** disable
access control globally with `xhost +`, expose X11 to the Internet, or disable
the firewall. X11 access grants substantial control over the graphical session.

### Example: native Linux Engine

Run from the graphical host session after setting `IMAGE` to the updated image
reference and `XAUTHORITY` to its readable authorization file:

```bash
mkdir -p "$PWD/shared"
docker run -d --name ac3e-desktop \
  --env "DISPLAY=$DISPLAY" \
  --env XAUTHORITY=/tmp/container.xauth \
  --mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly \
  --mount "type=bind,source=$XAUTHORITY,target=/tmp/container.xauth,readonly" \
  --mount "type=bind,source=$PWD/shared,target=/home/designer/shared" \
  "$IMAGE"
```

For a TCP server, omit the socket mount and replace `DISPLAY` with the appropriate
container-reachable address from the table. The authority file must authorize
that connection; copying a Unix-socket-only entry may not be sufficient. Create
the container from a shell if Docker Desktop's Run dialog does not expose all
required mounts/settings; subsequent Stop/Play operations can use the UI.

## Alternative without host X11

VNC/noVNC avoids host X11 socket and TCP-X11 differences on all three platforms.
Build the image with `ENABLE_GUI=1`, create a container using `--vnc --wait`,
set `VNC_PW`, and publish container port 80 to a loopback-only host port such as
`127.0.0.1:8080`. Open `http://localhost:8080/vnc.html` and launch a terminal in the
XFCE desktop. Play restarts the desktop service; it does not open a host window
or browser automatically. Keep passwords out of shared command logs.

## Existing command-line launchers

`make start` and `make start-raw` continue to use their attached shell rather
than opening an extra window. Batch commands and VNC behavior are unchanged.
A container originally created by these shell launchers retains its shell command:
recreate it using the X11 configuration above for the external-window Play flow.
