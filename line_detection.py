import cv2
import numpy as np


def get_center_points(mask, min_pixels=20, step=20, max_x_jump=80):
    """마스크 이미지를 y축 방향으로 나누고, 각 구간의 픽셀 중심점을 구한다."""
    height, width = mask.shape[:2]
    center_points = []

    last_x = None

    for y in range(height - 1, 0, -step):
        y_start = max(y - step, 0)
        y_end = y

        # 현재 y 구간만 잘라서 흰색 픽셀 위치를 찾는다.
        band = mask[y_start:y_end, :]
        ys, xs = np.where(band > 0)

        # 픽셀이 너무 적으면 차선이 아니라고 보고 무시한다.
        if len(xs) > min_pixels:
            center_x = int(np.mean(xs))
            center_y = int((y_start + y_end) / 2)

            # 이전 중심점과 너무 멀리 떨어진 점은 잘못 잡힌 점으로 보고 무시한다.
            if last_x is not None and abs(center_x - last_x) > max_x_jump:
                continue

            center_points.append((center_x, center_y))
            last_x = center_x

    return center_points


def draw_points_and_lines(image, points, color):
    """중심점들을 찍고, 점과 점 사이를 선으로 연결한다."""
    for point in points:
        cv2.circle(image, point, 4, color, -1)

    for i in range(len(points) - 1):
        cv2.line(image, points[i], points[i + 1], color, 3)

def points_to_dict(points):
    """중심점 리스트를 y좌표 기준 딕셔너리로 바꾼다."""
    return {y: x for x, y in points}

def make_target_points(left_points, right_points):
    """두 차선 중심점 사이의 중간점을 주행 기준선으로 만든다."""
    left_dict = points_to_dict(left_points)         # 왼쪽 차선 (y: x)
    right_dict = points_to_dict(right_points)       # 오른쪽 차선 (y: x)

    # (양쪽 차선이 모두 보이는) y좌표 골라내기
    target_points = []
    common_ys = sorted(set(left_dict.keys()) & set(right_dict.keys()), reverse=True)

    # 아래 -> 위 y좌표 순으로 중간점 계산 => 리스트에 추가
    for y in common_ys:
        center_x = int((left_dict[y] + right_dict[y]) / 2)
        target_points.append((center_x, y))

    return target_points

def shift_points(points, x_offset):
    """한쪽 차선만 보일 때 차선 폭을 가정해서 주행 기준선을 만든다."""
    target_points = []

    for x, y in points:
        target_points.append((int(x + x_offset), y))

    return target_points

def split_white_components_by_yellow(white_lane_mask, yellow_lane_mask, min_area=80):
    """
    흰색 차선을 먼저 연결된 덩어리로 나누고,
    각 덩어리를 노란 차선 기준으로 왼쪽/오른쪽에 분류한다.
    """
    height, width = white_lane_mask.shape[:2]

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        white_lane_mask,
        connectivity=8
    )

    # 전체 노란 차선의 기준 x를 구한다.
    _, yellow_xs = np.where(yellow_lane_mask > 0)

    if len(yellow_xs) > 10:
        reference_x = int(np.mean(yellow_xs))
    else:
        reference_x = width // 2

    left_white_mask = np.zeros((height, width), dtype=np.uint8)
    right_white_mask = np.zeros((height, width), dtype=np.uint8)

    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]

        if area < min_area:
            continue

        cx = centroids[label][0]

        component_mask = np.zeros((height, width), dtype=np.uint8)
        component_mask[labels == label] = 255

        if cx < reference_x:
            left_white_mask = cv2.bitwise_or(left_white_mask, component_mask)
        else:
            right_white_mask = cv2.bitwise_or(right_white_mask, component_mask)

    return left_white_mask, right_white_mask

def split_white_by_yellow(white_lane_mask, yellow_lane_mask, step=20):
    """
    흰색 차선을 노란 차선 기준으로 왼쪽/오른쪽으로 분리한다.
    화면 중앙 기준보다 코너에서 더 안정적이다.
    """
    height, width = white_lane_mask.shape[:2]

    left_white_mask = np.zeros((height, width), dtype=np.uint8)
    right_white_mask = np.zeros((height, width), dtype=np.uint8)

    last_reference_x = width // 2

    for y in range(height - 1, 0, -step):
        y_start = max(y - step, 0)
        y_end = y

        yellow_band = yellow_lane_mask[y_start:y_end, :]
        white_band = white_lane_mask[y_start:y_end, :]

        _, yellow_xs = np.where(yellow_band > 0)
        white_ys, white_xs = np.where(white_band > 0)

        if len(white_xs) == 0:
            continue

        # 해당 높이에 노란 차선이 보이면 그 위치를 기준으로 삼는다.
        if len(yellow_xs) > 5:
            reference_x = int(np.mean(yellow_xs))
            last_reference_x = reference_x
        else:
            # 노란 점선이 끊기는 구간에서는 이전 기준값을 사용한다.
            reference_x = last_reference_x

        # 흰색 픽셀을 기준선 왼쪽/오른쪽으로 나눈다.
        for wy, wx in zip(white_ys, white_xs):
            real_y = y_start + wy

            if wx < reference_x:
                left_white_mask[real_y, wx] = 255
            else:
                right_white_mask[real_y, wx] = 255

    return left_white_mask, right_white_mask


def show_front_camera(image):
    
# 받은 이미지 X
    if image is None:
        return False


# ROI 설정
    height, width = image.shape[:2]

    # 1. 도로 영역만 검출 (사다리꼴 ROI[원근법 - 중앙으로 갈수록 좁아지는 영역])
    roi_points = np.array([
        [
            (int(width * 0.02), height),
            (int(width * 0.35), int(height * 0.52)),
            (int(width * 0.65), int(height * 0.52)),
            (int(width * 0.98), height)
        ]
    ], dtype=np.int32)

    roi_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(roi_mask, roi_points, 255)

    # BGR -> HSV로 변환 (이미지 형식의 변환)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)


# 차선 검출 (노란색, 흰색)
    # 노란색 차선 mask처리
    lower_yellow = np.array([20, 80, 80])
    upper_yellow = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # 흰색 차선 mask처리
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([179, 60, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)

    # 1, 2차선 영역만 보기 (노란색 + 사다리꼴 ROI), (흰색 + 사다리꼴 ROI)
    yellow_lane_mask = cv2.bitwise_and(yellow_mask, roi_mask)
    white_lane_mask = cv2.bitwise_and(white_mask, roi_mask)
    
    # 노란색 : 점선으로 구성 => morphologyEx로 구멍 메꾸기
    yellow_kernel = np.ones((5, 15), np.uint8)
    yellow_lane_mask = cv2.morphologyEx(yellow_lane_mask, cv2.MORPH_CLOSE, yellow_kernel)


    # 노란색 차선(중앙) 기준 1, 2차선 나누기
# 흰색 차선을 연결된 덩어리 기준으로 왼쪽/오른쪽 나누기
    left_white_mask, right_white_mask = split_white_components_by_yellow(
        white_lane_mask,
        yellow_lane_mask,
        min_area=80
    )

    # 각 차선별 중심점 구하기 (차선 몇 개 보이는 지 pixel 개수로 판단, 노란색은 점선 때문에 min_pixels 낮게 설정)
    yellow_points = get_center_points(yellow_lane_mask, min_pixels=5, step=20, max_x_jump=160)
    left_white_points = get_center_points(left_white_mask, min_pixels=20, step=20, max_x_jump=80)
    right_white_points = get_center_points(right_white_mask, min_pixels=20, step=20, max_x_jump=80)
    
    # 주행 기준선 생성
    target_points = []

    # 차선 하나만 보일 때 사용할 임시 차선 절반 폭
    lane_half_width = int(width * 0.18)

    if len(yellow_points) >= 3 and len(right_white_points) >= 3:
        # 기본 주행: 노란 중앙선과 오른쪽 흰색 차선 사이
        target_points = make_target_points(yellow_points, right_white_points)

    elif len(left_white_points) >= 3 and len(yellow_points) >= 3:
        # 오른쪽 흰색 차선이 안 보이면 왼쪽 흰색 차선과 노란선 사이
        target_points = make_target_points(left_white_points, yellow_points)

    elif len(left_white_points) >= 3 and len(right_white_points) >= 3:
        # 노란선이 안 보이면 양쪽 흰색 차선 사이
        target_points = make_target_points(left_white_points, right_white_points)

    elif len(right_white_points) >= 3:
        # 오른쪽 흰색 차선만 보이면 왼쪽으로 차선 절반만큼 이동
        target_points = shift_points(right_white_points, -lane_half_width)

    elif len(yellow_points) >= 3:
        # 노란 중앙선만 보이면 오른쪽으로 차선 절반만큼 이동
        target_points = shift_points(yellow_points, lane_half_width)

    elif len(left_white_points) >= 3:
        # 왼쪽 흰색 차선만 보이면 오른쪽으로 차선 절반만큼 이동
        target_points = shift_points(left_white_points, lane_half_width)


    # cf. 차선 몇 개 보이는지 판단 (픽셀 개수 기준)
    yellow_visible = len(yellow_points) >= 3
    left_white_visible = len(left_white_points) >= 3
    right_white_visible = len(right_white_points) >= 3

    visible_lane_count = sum([
        yellow_visible,
        left_white_visible,
        right_white_visible
    ])

    # 통합 이미지
    masked_image = np.zeros_like(image)
    masked_image[yellow_lane_mask > 0] = (0, 255, 255)
    masked_image[left_white_mask > 0] = (255, 255, 255)
    masked_image[right_white_mask > 0] = (255, 255, 255)

    # 차선 구분하기
    draw_points_and_lines(masked_image, yellow_points, (0, 0, 255))          # 빨강: 노란 차선 중심선
    draw_points_and_lines(masked_image, left_white_points, (255, 0, 0))      # 파랑: 왼쪽 흰색 차선 중심선
    draw_points_and_lines(masked_image, right_white_points, (0, 255, 0))     # 초록: 오른쪽 흰색 차선 중심선
    draw_points_and_lines(masked_image, target_points, (255, 0, 255))        # 보라: 주행 기준선

    # 보이는 차선 개수 표시
    cv2.putText(
        masked_image,
        f"lanes: {visible_lane_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 255),
        2
    )

    cv2.imshow("Masked Lane Image", masked_image)




# 'q' 또는 ESC 키를 누르면 종료
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:
        return True

    return False