1.     통합플랫폼의 UDP/IP 수신 패킷의 payload 또한 최종 UDP/IP packet을 포함하도록 수정하였습니다.

2.     예제 소스는 통합플랫폼과 Data Server용으로 구분하여 보내드립니다.

	A.     ip_in_ip.c: 통합플랫폼 용 예제

	B.      udp_ip.c: Data Server 용 예제

3.     예제 소스의 시험 환경은 Ubuntu-18.04 입니다.




A.     unsigned char miot_local_ip[16] = "172.16.0.102\0";

B.      unsigned char miot_network_ip[16] = "172.16.0.10\0";

C.      unsigned char data_server_ip[16] = "172.16.0.2\0";