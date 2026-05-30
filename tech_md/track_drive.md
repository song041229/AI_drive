# TrackDriverNode 정의
class TrackDriverNode(Node):

    ### 클래스 생성 초기화 함수
    __init__(self)
        image           # 카메라 토픽 데이터를 저장할 변수
        motor_msg       # 모터토픽 메시지        
        lidar_ranges        
        bridge
        angle

        motor_pub       # 모터
        sub_front       # front 카메라
        subscription    # lider
    
## callback 함수
    ### 카메라 토픽을 수신하는 콜백 함수 
    def cam_callback(self, data)
        - 수신한 메시지(data)를 OpenCV 이미지로 변환하여 저장(image)
        - 저장한 이미지(image)를 line_detection.py에 넘겨주기(show_front_camera(image))
    
    ### 라이다 토픽을 수신하는 콜백 함수
    def lidar_callback(self, msg):
        

    ### 모터제어 토픽을 발행하는 Publisher 함수  
    def drive(self, angle, speed):
        - angle, speed만큼 모터제어 (차량 이동 함수)
        - line_detection에서 (키보드 입력, angle) 수신
            - angle로 drive() 조정
            - 'q' or ESC로 프로그램 종료

## main루프 정의
    ### 메인 루프
    def main_loop(self):
        angle
            - : 자회전
            + : 우회전 
            cf. 코너에선 +-80정도가 적당해보임

        speed
            1: 대략 2km/h
            10: 대략 18km/h
            20: 대략 35km/h

        while rclpy.ok():
            
            rclpy.spin_once(self, timeout_sec=0.0005)   # 쉽게 생각해서 처리할 콜백 속도 (timeout_sec가 작을수록 더 빨리 => fps 증가)
            drive(angle= ,speed= )                      # angle, speed로 차량 주행
                
                

# main 함수
def main(args=None):
      
    rclpy.init(args=args)
    node = TrackDriverNode()
	
    try:                        # main_loop() 함수를 호출
    except KeyboardInterrupt:   # (Ctrl+C) -> 그만
    finally:                    # 프로그램 종료
