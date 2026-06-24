import cv2
import numpy as np
import json

TILE_SIZE = 28

with open("cam_points.json") as f:
    cam_points = json.load(f)

with open("floor_points.json") as f:
    floor_points = json.load(f)

homographies = {}

for cam_name in ["cam1", "cam2", "cam3", "cam4"]:
    cp = cam_points[cam_name]
    fp = floor_points[cam_name]

    # only use labels that exist in both
    common = [l for l in cp if l in fp]
    print(f"\n{cam_name} — {len(common)} common points: {common}")

    if len(common) < 4:
        print(f"  [!] need at least 4, skipping")
        continue

    # pixel coords from camera
    src = np.float32([cp[l] for l in common])

    # tile coords → pixel coords on floor map
    dst = np.float32([
        [fp[l][0] * TILE_SIZE, fp[l][1] * TILE_SIZE]
        for l in common
    ])

    H, status = cv2.findHomography(src, dst, cv2.RANSAC)
    inliers = int(status.sum()) if status is not None else 0
    print(f"  homography computed — {inliers}/{len(common)} inliers")
    print(f"  matrix:\n{H}")

    homographies[cam_name] = H.tolist()

with open("homographies.json", "w") as f:
    json.dump(homographies, f, indent=2)

print("\nsaved → homographies.json")