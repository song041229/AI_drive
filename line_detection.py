import cv2


def show_front_camera(image):
    # 전면 카메라 이미지 X
    if image is None:
        return


    # 전면 카메라 이미지 O
    cv2.imshow("Front Camera", image)
    cv2.waitKey(1)