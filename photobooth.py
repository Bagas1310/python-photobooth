import os
os.environ["QT_QPA_PLATFORM"] = "xcb" 

import cv2
import numpy as np
import time
import pygame
import random
from datetime import datetime

pygame.mixer.init()

def draw_text_center(img, text, y, font_scale=1, thickness=2, color=(255, 255, 255)):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    x = (img.shape[1] - text_size[0]) // 2
    cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)

def apply_beauty_filter(frame):
    smooth = cv2.bilateralFilter(frame, 9, 75, 75)
    lab = cv2.cvtColor(smooth, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    merged = cv2.merge((l, a, b))
    result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return result

def overlay_image(background, overlay, x, y):
    h, w = overlay.shape[:2]
    if x >= background.shape[1] or y >= background.shape[0]:
        return background
     
    if x + w > background.shape[1]:
        w = background.shape[1] - x
        overlay = overlay[:, :w]
    if y + h > background.shape[0]:
        h = background.shape[0] - y
        overlay = overlay[:h, :]

    if overlay.shape[2] == 4:
        alpha = overlay[:, :, 3] / 255.0
        for c in range(3):
            background[y:y+h, x:x+w, c] = background[y:y+h, x:x+w, c] * (1 - alpha) + overlay[:, :, c] * alpha
    else:
        gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
         
        roi = background[y:y+h, x:x+w]
        bg_part = cv2.bitwise_and(roi, roi, mask=mask)
        fg_part = cv2.bitwise_and(overlay, overlay, mask=mask_inv)
        background[y:y+h, x:x+w] = cv2.add(bg_part, fg_part)
         
    return background

def main():
    cap = cv2.VideoCapture(0)
     
    if not cap.isOpened():
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    window_name = "Python Photobooth"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    captured_photos = []
    num_photos_needed = 3

    try:
        shutter_sound = pygame.mixer.Sound('shutter.mp3')
    except:
        shutter_sound = None
     
    is_capturing = False
     
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame = apply_beauty_filter(frame)

        screen_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        screen_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
         
        display_frame = cv2.resize(frame, (screen_w, screen_h))
         
        h, w, _ = display_frame.shape
        draw_text_center(display_frame, f"Tekan 'SPACE' untuk Foto ({len(captured_photos)}/{num_photos_needed})", 60, font_scale=1.0, thickness=2, color=(0, 255, 0))
        draw_text_center(display_frame, "Tekan 'ESC' untuk Keluar", h - 40, font_scale=0.7, thickness=2, color=(200, 200, 200))

        cv2.imshow(window_name, display_frame)

        key = cv2.waitKey(1) & 0xFF
         
        if key == 27:
            break
             
        elif key == ord(' ') and not is_capturing:
            is_capturing = True

            if shutter_sound:
                channel = shutter_sound.play()
                if channel:
                    pygame.time.delay(1100)
                    channel.stop()

            flash = np.ones_like(frame, dtype=np.uint8) * 255
            cv2.imshow(window_name, cv2.resize(flash, (screen_w, screen_h)))
            cv2.waitKey(150)
             
            captured_photos.append(frame.copy())
             
            if len(captured_photos) == num_photos_needed:
                strip_width = 560
                strip_height = 420
                 
                resized_list = [cv2.resize(p, (strip_width, strip_height)) for p in captured_photos]
                 
                padding = 45
                header_height = 80
                footer_height = 100
                total_w = strip_width + (padding * 2)
                total_h = (strip_height * num_photos_needed) + (padding * (num_photos_needed + 1)) + header_height + footer_height
                 
                strip = np.ones((total_h, total_w, 3), dtype=np.uint8) * 255
                 
                now = datetime.now()
                months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
                text_str = f"{now.day} {months_id[now.month - 1]} {now.year}"
                
                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 0.8
                thickness = 2
                text_size = cv2.getTextSize(text_str, font, font_scale, thickness)[0]
                text_x = (total_w - text_size[0]) // 2
                cv2.putText(strip, text_str, (text_x, 55), font, font_scale, (60, 60, 60), thickness, cv2.LINE_AA)
                 
                y_offset = padding + header_height
                for p in resized_list:
                    cv2.rectangle(strip, (padding - 2, y_offset - 2), (padding + strip_width + 2, y_offset + strip_height + 2), (220, 220, 220), 1)
                    strip[y_offset:y_offset+strip_height, padding:padding+strip_width] = p
                    y_offset += strip_height + padding
                 
                icon_size = 100
                
                icon_positions = [
                    (10, 10),
                    (total_w - icon_size - 10, 10),
                    (5, header_height - 5),
                    (total_w - icon_size - 5, header_height - 5),
                    (5, header_height + strip_height - 50),
                    (total_w - icon_size - 5, header_height + strip_height - 50),
                    (total_w - icon_size - 5, header_height + strip_height + padding - 5),
                    (5, header_height + strip_height * 2 - 50),
                    (5, header_height + strip_height * 2 + padding - 5),
                    (5, header_height + strip_height * 2 + padding + 60),
                    (total_w - icon_size - 5, header_height + strip_height * 2 + padding - 5),
                    (total_w - icon_size - 5, header_height + strip_height * 3 - 50),
                    (10, total_h - footer_height + 5),
                    (total_w // 3 - icon_size // 2, total_h - footer_height + 5),
                    (2 * total_w // 3 - icon_size // 2, total_h - footer_height + 5),
                    (total_w - icon_size - 10, total_h - footer_height + 5)
                ]

                all_files = [f for f in os.listdir("assets") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                
                if all_files:
                    for pos in icon_positions:
                        chosen_file = random.choice(all_files)
                        sticker_path = os.path.join("assets", chosen_file)
                        sticker_img = cv2.imread(sticker_path, cv2.IMREAD_UNCHANGED)
                         
                        if sticker_img is not None:
                            sticker_resized = cv2.resize(sticker_img, (icon_size, icon_size))
                            strip = overlay_image(strip, sticker_resized, pos[0], pos[1])

                folder_name = "Hasil Photo"
                os.makedirs(folder_name, exist_ok=True)
                filename = os.path.join(folder_name, f"photobooth_{int(time.time())}.jpg")
                cv2.imwrite(filename, strip)

                start_time = time.time()
                while time.time() - start_time < 5:
                    strip_display = cv2.resize(strip, (int(strip.shape[1] * screen_h / strip.shape[0]), screen_h)) if strip.shape[0] > screen_h else strip
                    canvas = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
                    x_start = (screen_w - strip_display.shape[1]) // 2
                    canvas[:, x_start:x_start+strip_display.shape[1]] = strip_display
                     
                    cv2.imshow(window_name, canvas)
                    if cv2.waitKey(100) & 0xFF == 27:
                        break
                 
                captured_photos = []

            time.sleep(0.3)
            is_capturing = False

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()