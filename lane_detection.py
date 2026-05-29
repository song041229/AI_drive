#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np

ROI_TOP_RATIO = 0.45
WHITE_LOWER  = np.array([0,   0,   190])
WHITE_UPPER  = np.array([180, 50,  255])
YELLOW_LOWER = np.array([15,  80,  80])
YELLOW_UPPER = np.array([35, 255, 255])
CANNY_LOW  = 50
CANNY_HIGH = 150
HOUGH_RHO        = 1
HOUGH_THETA      = np.pi / 180
HOUGH_THRESHOLD  = 25
HOUGH_MIN_LENGTH = 20
HOUGH_MAX_GAP    = 30
MIN_SLOPE = 0.3
MAX_SLOPE = 5.0
SMOOTH_ALPHA   = 0.35
OFFSET_WEIGHT  = 0.6
HEADING_WEIGHT = 0.4
OFFSET_GAIN    = 0.03
HEADING_GAIN   = 10.0
MAX_STEER      = 20.0

_prev_left  = None
_prev_right = None
_prev_steer = 0.0

def get_roi(image):
    h = image.shape[0]
    y_start = int(h * ROI_TOP_RATIO)
    return image[y_start:, :], y_start

def make_lane_mask(roi_bgr):
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    white_mask  = cv2.inRange(hsv, WHITE_LOWER,  WHITE_UPPER)
    yellow_mask = cv2.inRange(hsv, YELLOW_LOWER, YELLOW_UPPER)
    combined    = cv2.bitwise_or(white_mask, yellow_mask)
    kernel = np.ones((3, 3), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN,  kernel, iterations=1)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    return combined

def detect_lines(mask):
    edges = cv2.Canny(mask, CANNY_LOW, CANNY_HIGH)
    return cv2.HoughLinesP(edges, rho=HOUGH_RHO, theta=HOUGH_THETA,
                           threshold=HOUGH_THRESHOLD,
                           minLineLength=HOUGH_MIN_LENGTH,
                           maxLineGap=HOUGH_MAX_GAP)

def filter_and_separate_lines(lines, img_width):
    left_lines, right_lines = [], []
    if lines is None:
        return left_lines, right_lines
    cx = img_width / 2.0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        slope = (y2 - y1) / (x2 - x1)
        if abs(slope) < MIN_SLOPE or abs(slope) > MAX_SLOPE:
            continue
        mid_x = (x1 + x2) / 2.0
        if mid_x < cx:
            left_lines.append(line[0])
        else:
            right_lines.append(line[0])
    return left_lines, right_lines

def remove_outliers(lines, sigma=1.0):
    if len(lines) < 3:
        return lines
    slopes = [(y2 - y1) / (x2 - x1) for x1, y1, x2, y2 in lines if x2 != x1]
    if not slopes:
        return lines
    median = np.median(slopes)
    std    = np.std(slopes)
    if std < 1e-6:
        return lines
    filtered = [seg for seg in lines
                if abs(((seg[3]-seg[1])/(seg[2]-seg[0])) - median) <= sigma * std
                if seg[2] != seg[0]]
    return filtered if filtered else lines

def average_line(lines, img_height, roi_y):
    if not lines:
        return None
    lines = remove_outliers(lines)
    slopes, intercepts, weights = [], [], []
    for x1, y1, x2, y2 in lines:
        if x2 == x1:
            continue
        length    = np.hypot(x2 - x1, y2 - y1)
        slope     = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        slopes.append(slope)
        intercepts.append(intercept)
        weights.append(length)
    if not slopes:
        return None
    total_w = sum(weights)
    m = sum(s * w for s, w in zip(slopes,     weights)) / total_w
    b = sum(i * w for i, w in zip(intercepts, weights)) / total_w
    if abs(m) < 1e-6:
        return None
    y_bottom_roi = img_height - 1 - roi_y
    x_bottom = int((y_bottom_roi - b) / m)
    x_top    = int((0            - b) / m)
    return (x_top, roi_y, x_bottom, img_height - 1)

def smooth_line(current, previous, alpha=SMOOTH_ALPHA):
    if current is None:
        return previous
    if previous is None:
        return current
    return tuple(int(alpha * c + (1 - alpha) * p) for c, p in zip(current, previous))

def get_slope(line):
    x1, y1, x2, y2 = line
    if x2 == x1:
        return None
    return (y2 - y1) / (x2 - x1)

def calc_steer(left_line, right_line, img_width):
    """
    offset  : 두 차선 하단 중점과 화면 중앙의 픽셀 차이 → 위치 보정
    heading : 차선 기울기 평균 → 커브 예측 보정
    steer   = OFFSET_WEIGHT * offset_angle + HEADING_WEIGHT * heading_angle
    한쪽만 보일 때는 보이는 차선 기준으로 추정.
    차선 없으면 이전 조향각 유지.
    """
    global _prev_steer
    cx = img_width / 2.0

    if left_line is not None and right_line is not None:
        mid_x  = (left_line[2] + right_line[2]) / 2.0
        offset = mid_x - cx
        slopes = [s for s in [get_slope(left_line), get_slope(right_line)] if s is not None]
        avg_slope     = np.mean(slopes) if slopes else 0.0
        heading_angle = -np.degrees(np.arctan(avg_slope)) * (HEADING_GAIN / 90.0)
        offset_angle  = offset * OFFSET_GAIN
        steer = OFFSET_WEIGHT * offset_angle + HEADING_WEIGHT * heading_angle

    elif left_line is not None:
        offset = left_line[2] - cx * 0.5
        s = get_slope(left_line)
        heading_angle = -np.degrees(np.arctan(s)) * (HEADING_GAIN / 90.0) if s else 0.0
        steer = OFFSET_WEIGHT * (offset * OFFSET_GAIN) + HEADING_WEIGHT * heading_angle

    elif right_line is not None:
        offset = right_line[2] - cx * 1.5
        s = get_slope(right_line)
        heading_angle = -np.degrees(np.arctan(s)) * (HEADING_GAIN / 90.0) if s else 0.0
        steer = OFFSET_WEIGHT * (offset * OFFSET_GAIN) + HEADING_WEIGHT * heading_angle

    else:
        return _prev_steer

    steer = float(np.clip(steer, -MAX_STEER, MAX_STEER))
    _prev_steer = steer
    return steer

def draw_lane_lines(image, left_line, right_line, steer):
    overlay = image.copy()
    h, w = image.shape[:2]

    if left_line is not None:
        cv2.line(overlay, (left_line[0], left_line[1]),
                           (left_line[2], left_line[3]), (255, 50, 50), 4)
    if right_line is not None:
        cv2.line(overlay, (right_line[0], right_line[1]),
                           (right_line[2], right_line[3]), (50, 255, 50), 4)

    if left_line is not None and right_line is not None:
        cx_lane = (left_line[2] + right_line[2]) // 2
        cy_lane = (left_line[3] + right_line[3]) // 2
        offset  = cx_lane - w // 2
        cv2.circle(overlay, (cx_lane, cy_lane), 8, (0, 0, 255), -1)
        cv2.line(overlay, (w // 2, h - 20), (cx_lane, cy_lane), (0, 0, 255), 2)
        cv2.putText(overlay, f"offset: {offset:+d}px",
                    (w // 2 - 70, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

    cv2.putText(overlay, f"steer: {steer:+.1f} deg",
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    arrow_x = w // 2 + int(steer * 2)
    cv2.arrowedLine(overlay, (w // 2, h - 60), (arrow_x, h - 60),
                    (0, 200, 255), 3, tipLength=0.3)

    return overlay

def process_image(image):
    """
    반환:
        viz_image  : 시각화 이미지
        left_line  : (x1,y1,x2,y2) 또는 None
        right_line : (x1,y1,x2,y2) 또는 None
        steer      : 조향각 degree (양수=오른쪽, 음수=왼쪽)
        debug_dict : {'mask':..., 'roi':...}
    """
    global _prev_left, _prev_right

    h, w = image.shape[:2]
    roi, roi_y = get_roi(image)
    mask       = make_lane_mask(roi)
    lines      = detect_lines(mask)

    left_lines, right_lines = filter_and_separate_lines(lines, w)

    left_line  = smooth_line(average_line(left_lines,  h, roi_y), _prev_left)
    right_line = smooth_line(average_line(right_lines, h, roi_y), _prev_right)

    _prev_left  = left_line
    _prev_right = right_line

    steer     = calc_steer(left_line, right_line, w)
    viz_image = draw_lane_lines(image.copy(), left_line, right_line, steer)
    cv2.line(viz_image, (0, roi_y), (w, roi_y), (0, 255, 255), 1)

    return viz_image, left_line, right_line, steer, {'mask': mask, 'roi': roi}

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("사용법: python3 lane_detection.py <이미지파일>")
        sys.exit(1)
    img = cv2.imread(sys.argv[1])
    if img is None:
        print("이미지 로드 실패:", sys.argv[1])
        sys.exit(1)
    viz, left, right, steer, dbg = process_image(img)
    print(f"왼쪽 차선: {left}")
    print(f"오른쪽 차선: {right}")
    print(f"조향각: {steer:+.1f} deg")
    cv2.imshow("Lane Detection", viz)
    cv2.imshow("Mask", dbg['mask'])
    cv2.waitKey(0)
    cv2.destroyAllWindows()