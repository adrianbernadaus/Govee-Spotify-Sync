# Govee Spotify Sync

A lightweight python script to synchronize your Govee LED Strip (Bluetooth) with your Spotify music.
It continuously monitors your current playing track on Spotify, extracts the dominant vibrant color from the album art, and smoothly transitions your LED strip to match.

## Features
- **Persistent Bluetooth Connection**: Advanced keep-alive logic maintains stability with the Govee device.
- **Smart Color Extraction**: Analyzes album art to find the most vibrant, suitable color (ignoring dull blacks/grays).
- **Background Operation**: Optimized to run efficiently in the background.

## Requirements
- Python 3.8+
- Govee LED Strip (Bluetooth enabled)
- Spotify Premium (for API access)

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/govee-spotify-sync.git
    cd govee-spotify-sync
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure Secrets:
    -   Rename `.env.example` to `.env`.
    -   Open `.env` and fill in your details:
        -   `DEVICE_MAC`: The Bluetooth MAC Address of your Govee device (e.g., `A4:C1:38...`).
        -   `SPOTIFY_CLIENT_ID` & `SECRET`: From your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).

## Usage

Run the script:
```bash
python govee_sync.py
```

## Disclaimer
This project is not affiliated with Govee or Spotify. Use at your own risk.
