import asyncio
import logging
import requests
import colorsys
import io
import time
import os
from PIL import Image
from bleak import BleakClient
from spotipy import Spotify
from spotipy.oauth2 import SpoifyOAuth
from dotenv import load_dotenv

load_dotenv()

DEVICE_MAC = os.getenv("DEVICE_MAC")
GOVEE_BT_CMD_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SPOTIFY_SCOPE = "user-read-currently-playing"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GoveeSync")

class GoveeController:
    def __init__(self, mac_address):
        self.mac_address = mac_address
        self.client = None
        self.current_rgb = (0, 0, 0)
        self._disconnect_event = asyncio.Event()

    def _on_disconnect(self, client):
        logger.warning(f"Device {client.address} disconnected unexpectedly!")
        self.client = None
        
    async def ensure_connected(self):
        if self.client and self.client.is_connected:
            return True
            
        logger.info(f"Connecting to BLE {self.mac_address}...")
        try:
            self.client = BleakClient(self.mac_address, disconnected_callback=self._on_disconnect)
            await self.client.connect()
            logger.info("BLE Connected.")
            return True
        except Exception as e:
            logger.error(f"BLE Connect Error: {e}")
            self.client = None
            return False
            
    async def disconnect(self):
        if self.client:
            await self.client.disconnect() 
            self.client = None 

    async def send_packet(self, r, g, b):
        if not self.client or not self.client.is_connected: return False
        try:
            payload = bytearray([0x33, 0x05, 0x02, r, g, b])
            payload.extend([0] * (19 - len(payload)))
            checksum = 0
            for byte in payload: checksum ^= byte
            payload.append(checksum)
            
            await self.client.write_gatt_char(GOVEE_BT_CMD_UUID, payload, response=False)
            
            await asyncio.sleep(0) 
            return True
        except Exception as e:
            logger.error(f"BLE Write Error: {e}")
            return False

    async def fade_to_color(self, r, g, b, duration=1.0):
        if not await self.ensure_connected(): return

        start_r, start_g, start_b = self.current_rgb
        if (start_r, start_g, start_b) == (r, g, b): return

        steps = 8 
        delay = duration / steps
        
        if delay < 0.1: 
            delay = 0.1
            steps = int(duration / delay)
            if steps < 1: steps = 1

        for i in range(1, steps + 1):
            factor = i / steps
            new_r = int(start_r + (r - start_r) * factor)
            new_g = int(start_g + (g - start_g) * factor)
            new_b = int(start_b + (b - start_b) * factor)
            
            await self.send_packet(new_r, new_g, new_b)
            await asyncio.sleep(delay)
            
        self.current_rgb = (r, g, b)

    async def send_keep_alive(self):
        if not await self.ensure_connected():
            return
            
        try:
            payload = bytearray([0xAA, 0x01])
            payload.extend([0] * (19 - len(payload)))
            checksum = 0
            for byte in payload: checksum ^= byte
            payload.append(checksum)
            
            logger.info("Sending Status Query (Heartbeat)...")
            await self.client.write_gatt_char(GOVEE_BT_CMD_UUID, payload, response=False)
        except Exception as e:
            logger.error(f"Heartbeat Failed: {e}")

def get_vibrant_color(image):
    try:
        image.thumbnail((100, 100))
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pixels = list(image.getdata())
            
        best_color = (255, 255, 255)
        max_score = -1
        
        for i in range(0, len(pixels), 50):
            r, g, b = pixels[i]
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            score = (s * 3.0) + (v * 1.0)
            if v < 0.15: score -= 5.0
            if s < 0.1: score -= 2.0
            if score > max_score:
                max_score = score
                best_color = (r, g, b)
        return best_color
    except Exception as e:
        logger.error(f"Color Error: {e}")
        return (255, 255, 255)

async def main():
    logger.info("Starting Govee Spotify Sync...")
    
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        open_browser=False
    )
    sp = Spotify(auth_manager=auth_manager)
    
    govee = GoveeController(DEVICE_MAC)
    await govee.ensure_connected()
    
    last_img_url = None
    last_packet_time = time.time()
    
    try:
        while True:
            try:
                track = sp.current_user_playing_track()
                if track and track['is_playing']:
                    item = track['item']
                    if item and 'album' in item and item['album']['images']:
                        img_url = item['album']['images'][0]['url']
                        
                        if img_url != last_img_url:
                            logger.info(f"New Song: {item['name']}")
                            resp = requests.get(img_url)
                            img = Image.open(io.BytesIO(resp.content))
                            
                            r, g, b = get_vibrant_color(img)
                            logger.info(f"Detected Vibrant Color:RGB({r},{g},{b})")
                            
                            await govee.fade_to_color(r, g, b)
                            last_img_url = img_url
                    
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(2)
                
                if time.time() - last_packet_time > 2:
                    await govee.send_keep_alive()
                    last_packet_time = time.time()
                    
            except requests.exceptions.ReadTimeout:
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(5)
                
    except KeyboardInterrupt:
        logger.info("Stopping...")
        await govee.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
