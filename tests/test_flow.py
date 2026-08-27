# בדיקה אלגוריתמית: מדמה שני פריימים של רקע נע + מיסוך פנים,
# מריצה את אותה לוגיקה כמו MotionEngine ומאמתת את הווקטור.
import cv2
import numpy as np

np.random.seed(1)
base = (np.random.rand(480, 640) * 255).astype(np.uint8)
shift_x, shift_y = 8, -5
prev = base.copy()
cur = np.roll(base, shift_y, axis=0)
cur = np.roll(cur, shift_x, axis=1)

# מיסוך "פנים" במרכז - בדיוק כמו _build_feature_image
feat = cur.copy()
feat[180:320, 260:400] = 0
corners = cv2.goodFeaturesToTrack(feat, 120, 0.01, 10, 7)
assert corners is not None and len(corners) >= 10, "NO FEATURES"

p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, corners, None,
                                     winSize=(21, 21), maxLevel=3)
good = st.flatten() == 1
vectors = (p1[good] - corners[good]).reshape(-1, 2)
mx, my = np.median(vectors, axis=0)
print("EXPECTED_SHIFT=(8,-5) MEASURED=(%.2f, %.2f) FEATURES=%d"
      % (mx, my, good.sum()))
assert abs(mx - 8) < 1.5 and abs(my + 5) < 1.5, "FLOW MISMATCH"

# ודא שאין נקודות מעקב בתוך אזור הפנים הממוסך
inside = ((corners[:, 0, 0] >= 260) & (corners[:, 0, 0] <= 400) &
          (corners[:, 0, 1] >= 180) & (corners[:, 0, 1] <= 320)).sum()
print("POINTS_INSIDE_FACE_MASK=%d" % inside)
assert inside == 0, "FACE MASK LEAK"

print("FLOW_TEST_OK")
