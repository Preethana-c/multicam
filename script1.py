import cv2
import numpy as np

# Camera 0 homography from calibration file
H = np.array([
    [0.176138,  0.647589, -63.412272],
    [-0.180912, 0.622446,  -0.125533],
    [-0.000002, 0.001756,   0.102316]
])

def click_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        pt = np.array([[[x, y]]], dtype=np.float32)
        floor_pt = cv2.perspectiveTransform(pt, H)
        fx, fy = floor_pt[0][0]
        print(f"Pixel ({x}, {y})  →  Floor ({fx:.1f}, {fy:.1f})")

# Load first frame
cap = cv2.VideoCapture(r"C:\Preethi\multi_cam\camera_vid\4p-c1.avi")
ret, frame = cap.read()
cap.release()

cv2.imshow("Camera 0 - click to project", frame)
cv2.setMouseCallback("Camera 0 - click to project", click_callback)
cv2.waitKey(0)
cv2.destroyAllWindows()