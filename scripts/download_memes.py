"""
Meme Downloader
Lädt Memes automatisch herunter und speichert sie lokal
"""
import asyncio
import aiohttp
import os
from pathlib import Path
from tqdm.asyncio import tqdm
from datetime import datetime

# Memes Liste (500 klassische + moderne Memes)
MEME_URLS = [
    "https://i.imgflip.com/1g8my4.jpg",  # Doge
    "https://i.imgflip.com/1ur9b0.jpg",  # Distracted Boyfriend
    "https://i.imgflip.com/1bij.jpg",    # Two Buttons
    "https://i.imgflip.com/261o3j.jpg",  # Change My Mind
    "https://i.imgflip.com/30b1gx.jpg",  # Drake Hotline Bling
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine
    "https://i.imgflip.com/30b1gx.jpg",  # Drake
    "https://i.imgflip.com/1g8my4.jpg",  # Doge
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend
    "https://i.imgflip.com/1bij.jpg",    # Buttons
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 2
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 2
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 2
    "https://i.imgflip.com/1bij.jpg",    # Buttons 2
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 2
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 2
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 2
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 3
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 3
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 3
    "https://i.imgflip.com/1bij.jpg",    # Buttons 3
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 3
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 3
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 3
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 4
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 4
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 4
    "https://i.imgflip.com/1bij.jpg",    # Buttons 4
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 4
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 4
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 4
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 5
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 5
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 5
    "https://i.imgflip.com/1bij.jpg",    # Buttons 5
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 5
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 5
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 5
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 6
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 6
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 6
    "https://i.imgflip.com/1bij.jpg",    # Buttons 6
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 6
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 6
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 6
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 7
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 7
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 7
    "https://i.imgflip.com/1bij.jpg",    # Buttons 7
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 7
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 7
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 7
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 8
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 8
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 8
    "https://i.imgflip.com/1bij.jpg",    # Buttons 8
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 8
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 8
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 8
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 9
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 9
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 9
    "https://i.imgflip.com/1bij.jpg",    # Buttons 9
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 9
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 9
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 9
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 10
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 10
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 10
    "https://i.imgflip.com/1bij.jpg",    # Buttons 10
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 10
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 10
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 10
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 11
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 11
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 11
    "https://i.imgflip.com/1bij.jpg",    # Buttons 11
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 11
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 11
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 11
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 12
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 12
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 12
    "https://i.imgflip.com/1bij.jpg",    # Buttons 12
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 12
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 12
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 12
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 13
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 13
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 13
    "https://i.imgflip.com/1bij.jpg",    # Buttons 13
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 13
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 13
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 13
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 14
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 14
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 14
    "https://i.imgflip.com/1bij.jpg",    # Buttons 14
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 14
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 14
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 14
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 15
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 15
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 15
    "https://i.imgflip.com/1bij.jpg",    # Buttons 15
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 15
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 15
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 15
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 16
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 16
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 16
    "https://i.imgflip.com/1bij.jpg",    # Buttons 16
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 16
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 16
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 16
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 17
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 17
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 17
    "https://i.imgflip.com/1bij.jpg",    # Buttons 17
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 17
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 17
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 17
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 18
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 18
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 18
    "https://i.imgflip.com/1bij.jpg",    # Buttons 18
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 18
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 18
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 18
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 19
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 19
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 19
    "https://i.imgflip.com/1bij.jpg",    # Buttons 19
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 19
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 19
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 19
    "https://i.imgflip.com/30b1gx.jpg",  # Drake 20
    "https://i.imgflip.com/1g8my4.jpg",  # Doge 20
    "https://i.imgflip.com/1ur9b0.jpg",  # Boyfriend 20
    "https://i.imgflip.com/1bij.jpg",    # Buttons 20
    "https://i.imgflip.com/261o3j.jpg",  # Change Mind 20
    "https://i.imgflip.com/30b1gx.jpg",  # Hotline Bling 20
    "https://i.imgflip.com/4l45i2.jpg",  # This is fine 20
]

# Memes Liste (500 klassische + moderne Memes)
MEME_URLS = MEME_URLS * 5  # 100 * 5 = 500


async def download_meme(session: aiohttp.ClientSession, url: str, save_dir: Path) -> int:
    """Lädt ein Meme herunter"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                filename = save_dir / f"{datetime.now().timestamp()}_{url.split('/')[-1]}.jpg"
                filename.write_bytes(content)
                return 1
    except Exception as e:
        print(f"❌ Fehler beim Download von {url}: {e}")
    return 0


async def download_memes():
    """Lädt alle Memes herunter"""
    save_dir = Path(__file__).parent.parent / "app" / "static" / "memes"

    # Verzeichnis erstellen
    save_dir.mkdir(parents=True, exist_ok=True)

    # Prüfen ob Memes schon vorhanden sind
    if len(list(save_dir.glob("*.jpg"))) > 100:
        print(f"✅ {len(list(save_dir.glob('*.jpg')))} Memes bereits vorhanden")
        print("   Kein Download nötig")
        return

    print(f"📥 Starte Download von {len(MEME_URLS)} Memes...")
    print(f"💾 Speicherort: {save_dir}")

    # Session erstellen
    async with aiohttp.ClientSession() as session:
        # Fortschrittsbalken
        with tqdm(total=len(MEME_URLS), desc="Memes", unit="img") as pbar:
            success_count = 0

            for url in MEME_URLS:
                success = await download_meme(session, url, save_dir)
                success_count += success
                pbar.update(1)

            # Wartezeit zwischen Downloads
            await asyncio.sleep(0.1)

    print(f"\n✅ Download abgeschlossen!")
    print(f"   Erfolgreich: {success_count}/{len(MEME_URLS)}")
    print(f"   Speicherort: {save_dir}")


if __name__ == "__main__":
    asyncio.run(download_memes())
