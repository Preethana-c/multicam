import cv2
import numpy as np
import json

TILE_SIZE = 28

with open("homographies.json") as f:
    homographies = {cam: np.array(H) for cam, H in json.load(f).items()}

def pixel_to_tile(cam_name, px, py):
    H = homographies[cam_name]
    
    # apply homography
    pt = np.array([[[px, py]]], dtype=np.float32)
    result = cv2.perspectiveTransform(pt, H)
    
    # result is in floor map pixels → convert to tile
    floor_px = result[0][0][0]
    floor_py = result[0][0][1]
    
    tile_col = int(floor_px / TILE_SIZE)
    tile_row = int(floor_py / TILE_SIZE)
    
    return tile_col, tile_row

# test it
print(pixel_to_tile("cam1", 580, 113))   # should be near tile (18, 6)
print(pixel_to_tile("cam2", 21, 87))     # should be near tile (0, 27)
print(pixel_to_tile("cam3", 313, 315))   # should be near tile (5, 3)
print(pixel_to_tile("cam4", 293, 224))   # should be near tile (5, 19)