<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# RTSP to MJPEG with On-Demand FFmpeg: Full Documentation

This documentation describes a containerized solution for converting an RTSP video stream to an MJPEG (Motion JPEG) HTTP stream, providing features for efficient on-demand process management and robust health checking. The solution uses FFmpeg, but improves upon the default behavior by running FFmpeg only when at least one client is connected—dramatically reducing unnecessary CPU usage. It is suitable for Kubernetes, Docker Compose, and standalone Docker CLI usage.

## Features

- **On-demand FFmpeg:**
FFmpeg runs only when a viewer is actively connected to your HTTP MJPEG stream. This saves CPU and memory compared to always-on solutions.
- **Flexible deployment:**
Supports deployment with Docker Compose, raw Docker CLI, and Kubernetes.
- **Health checks:**
Exposes a lightweight HTTP endpoint (`/` on port 8092) for readiness/liveness probes.
- **Configurable:**
All sensitive values (RTSP URL, etc.) can be set with environment variables or secrets.
- **Clear Stream Access:**
    - MJPEG stream: `http://<host>:8090/live.mjpg`
    - Snapshot: `http://<host>:8090/still.jpg`


## Table of Contents

- [Environment Variables](#environment-variables)
- [How On-Demand Streaming Works](#how-on-demand-streaming-works)
- [Script (`forward.py`) Description](#script-forwardpy-description)
- [Docker Compose Example](#docker-compose-example)
- [Docker CLI Example](#docker-cli-example)
- [Kubernetes Deployment Reference](#kubernetes-deployment-reference)
- [Sample Usage](#sample-usage)
- [Comparison: This Fork vs Default Versions](#comparison-this-fork-vs-default-versions)
- [Tips and Additional Info](#tips-and-additional-info)


## Environment Variables

| Variable | Purpose | Example/Default |
| :-- | :-- | :-- |
| `RTSP_URL` | RTSP input stream URL | `rtsp://username:password@host:port/path` |
| `FFSERVER_LOG_LEVEL` | Log level for FFserver | `error` (default) |
| `FFMPEG_LOG_LEVEL` | Log level for FFmpeg | `warning` (default) |
| `FFMPEG_INPUT_OPTS` | FFmpeg input options | (usually not needed) |
| `FFMPEG_OUTPUT_OPTS` | FFmpeg output options | (usually not needed) |

Set these in your `.env` file or via secrets as appropriate.

## How On-Demand Streaming Works

Unlike traditional containerizations where FFmpeg runs continuously, this solution improves efficiency by launching FFmpeg **only when at least one client is connected** to the MJPEG stream. Once all clients disconnect, FFmpeg is stopped after a configurable grace period. This reduces idle resource consumption significantly.

## Script (`forward.py`) Description

The core of this on-demand behavior is the `forward.py` script. It has several roles:

- **Connection and process management:**
Listens for incoming HTTP connections. When the first client connects, it launches FFmpeg (using a shell script such as `stream.sh`). If all viewers disconnect, it stops FFmpeg after the timeout period.
- **Data proxying:**
Forwards stream data between the FFmpeg process and the active client(s) using threads to allow simultaneous reading/writing.
- **Health check server:**
Runs a separate lightweight HTTP server (default port `8092`). Returns status `200` with `"health ok"` when queried, allowing Docker/Kubernetes to monitor service health.
- **Timeouts for idle connections:**
Safely kills streaming if clients disconnect, but only after a configurable timeout. Prevents unnecessary resource usage in the absence of viewers.
- **Error handling and logging:**
Robust handling of unexpected network/process errors and clean log output for diagnostics.

*Note: The script itself isn’t included here, but this summary describes its purpose and architectural role.*

## Docker Compose Example

```yaml
version: '3.8'

services:
  rtsp2mjpg:
    image: docker.io/krab55/rtsp2mjpg:latest
    container_name: rtsp2mjpg
    restart: unless-stopped
    ports:
      - "8090:8090"    # MJPEG stream
      - "8092:8092"    # Health check/readiness
    environment:
      - RTSP_URL=${RTSP_URL}
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8092/"]
      interval: 10s
      timeout: 2s
      retries: 3
      start_period: 15s
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
```

**How to use:**

1. Create a `.env` file **(never commit this to source control!)**:

```
RTSP_URL=rtsp://your_username:your_password@camera-host:554/stream-path
```

2. Launch with:

```
docker-compose up -d
```

3. Access streams:
    - MJPEG: `http://<host>:8090/live.mjpg`
    - JPEG snapshot: `http://<host>:8090/still.jpg`

## Docker CLI Example

1. **Export the RTSP URL (safest, avoids leaking credentials):**

```sh
export RTSP_URL="rtsp://username:password@host:port/path"
```

2. **Run the container:**

```sh
docker run -d \
  --name rtsp2mjpg \
  -p 8090:8090 \
  -p 8092:8092 \
  -e RTSP_URL="$RTSP_URL" \
  --restart unless-stopped \
  --cpus="0.5" \
  --memory="512m" \
  docker.io/krab55/rtsp2mjpg:latest
```

3. **(Optional) Add health check using Docker CLI:**

```sh
docker update --health-cmd="curl --fail http://localhost:8092/" \
  --health-interval=10s \
  --health-timeout=2s \
  --health-retries=3 \
  --health-start-period=15s \
  rtsp2mjpg
```


## Kubernetes Deployment Reference (for advanced users)

Shortened for clarity (refer to prior message for full details):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rtsp2mjpg
spec:
  template:
    spec:
      containers:
        - name: rtsp2mjpg
          image: docker.io/krab55/rtsp2mjpg:latest
          ports:
            - containerPort: 8090
            - containerPort: 8092
          env:
            - name: RTSP_URL
              valueFrom:
                secretKeyRef:
                  name: rtsp2mjpg
                  key: RTSP_URL
          resources:
            limits:
              cpu: "500m"
              memory: "512M"
          readinessProbe:
            httpGet:
              path: /
              port: 8092
```

Expose service as needed for external access.

## Sample Usage

- **Watch the live MJPEG stream (in a browser or compatible app):**

```
http://localhost:8090/live.mjpg
```

- **Grab a JPEG snapshot:**

```
http://localhost:8090/still.jpg
```

- **Get health status (for Docker/Kubernetes/resiliency):**

```
curl http://localhost:8092/
# Should return: health ok
```


## Comparison: This Fork vs Default Versions

| Feature | This Fork | Default Version |
| :-- | :-- | :-- |
| **FFmpeg Lifetime** | On-demand—runs only if a viewer is present | Always running |
| **CPU/Resource Efficiency** | Significantly lower with many idle periods | Potentially wasteful |
| **Health Check** | Built-in HTTP endpoint on port 8092 | Usually none |
| **Script:** `forward.py` | Manages connections \& FFmpeg lifecycle | Default: no such script |
| **Graceful Shutdown** | Waits, times out, stops unnecessary ffmpeg | May leak CPU/memory |

## Tips and Additional Info

- **Security:**
Never log or share your actual RTSP URL. Use environment variables and/or Kubernetes secrets.
- **Customization:**
You can customize FFmpeg arguments by exposing more environment variables or edit the launch script as needed.
- **Nginx Proxy:**
For production, consider running this behind an Nginx (or other HTTP) proxy for even better reliability and access control.

This solution is highly suitable for production scenarios where resource usage matters, or for cloud/batch deployments where not all users require continuous streaming. The on-demand model, robust health checks, and flexible deployment options provide a compelling upgrade over default MJPEG conversion images.

