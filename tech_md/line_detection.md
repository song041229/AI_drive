import cv2
import numpy as np

## get_center_points()
def get_center_points(mask, min_pixels=20, step=20):
    - 마스크 이미지를 y축 방향으로 나누기

    - 각 구간의 픽셀 중심점을 구하기
    for y in range(height - 1, 0, -step):
        - 현재 y 구간만 잘라서 흰색 픽셀 위치를 찾는다.
        - 픽셀 너무 작음 -> 무시

    return center_points

## draw_points_and_lines()
def draw_points_and_lines(image, points, color):
    - 중심점 찍기
    - 점과 점 사이 연결

## split_white_by_yellow()
def split_white_by_yellow(white_lane_mask, yellow_lane_mask, step=20):
    - 노란색 기준 흰색(왼쪽, 오른쪽) 나누기
    
    for y in range(height - 1, 0, -step):
        
        - 이미지 아래 -> 위로 파악
        - 노란차선 x의 위치 파악하기 (그 x의 높이가 기준선)

        _, yellow_xs = 노란 차선 찾기
        white_ys, white_xs = np.where(white_band > 0)
        if len(white_xs) == 0   //흰색 차선 X => 다음구간 넘어가기


        ### 노란 차선 검출 -> 그 위치 = 기준
        if len(yellow_xs) > 5:
        else:

        ### 노란차선 기준 wx 비교 => 흰색 차선(1, 2차선) 나누기
        for wy, wx in zip(white_ys, white_xs):
            if wx < reference_x:    //현재 픽셀 wx가 노란차선보다 왼쪽 -> left_white
            else:                   //현재 픽셀이 노란차선보다 오른쪽 -> right_white

    return left_white_mask, right_white_mask

## show_fromt_camera
def show_front_camera(image):
    
## 받은 이미지 X
    if image is None:
        return False


## ROI 설정
    height, width = image.shape[:2]

    ### 도로 영역만 검출 (사다리꼴 ROI[원근법 - 중앙으로 갈수록 좁아지는 영역])
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

    ### BGR -> HSV로 변환 (이미지 형식의 변환)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)


## 차선 검출 (노란색, 흰색)
    ### 노란색 차선 mask처리
    lower_yellow = np.array([20, 80, 80])
    upper_yellow = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    ### 흰색 차선 mask처리
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([179, 60, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)

    ### 차선 영역만 보기 (노란색 + 사다리꼴 ROI), (흰색 + 사다리꼴 ROI)
    - 노란색 = bitwise()
    - 흰색 = bitwise()

    ### 노란색 차선(중앙) 기준 1, 2차선 나누기
    - 오른쪽, 왼쪽 = split_white_by_yellow()

    ### 각 차선별 중심점 구하기 (차선 몇 개 보이는 지 pixel 개수로 판단)
    - 노란색 = get_center_points(노란색 mask, 기준 완화[점선])
    - 오른쪽 흰색 = get_center_points(오른쪽 흰색 mask)
    - 왼쪽 흰색 = get_center_points(왼쪽 흰색 mask)

    # cf. 차선 몇 개 보이는지 판단 (픽셀 개수 기준)
    - if (len() >= 3)로 각 차선 판별
    - visible_lane_count = sum([차선 인식 개수])

    # 통합 이미지
    # 차선 구분하기
    (masked_image, 중앙)      # 빨강: 노란 차선 중심선
    (masked_image, 왼쪽)      # 파랑: 왼쪽 흰색 차선 중심선
    (masked_image, 오른쪽)     # 초록: 오른쪽 흰색 차선 중심선

    # 보이는 차선 개수 표시
    cv2.putText(
        masked_image,
        # 0, 1, 2, 3개 중 띄우기
    )
    
    # 이미지 띄우기
    cv2.imshow()


## 'q' 또는 ESC 키를 누르면 종료
