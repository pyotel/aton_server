# ATON Server

항로표지(Aids To Navigation) 관리 시스템을 위한 MSA(Microservice Architecture) 기반 서버입니다.

## 개요

ATON Server는 항로표지 IoT 장비로부터 데이터를 수집하고 관리하는 시스템입니다. MQTT를 통한 실시간 데이터 수집과 InfluxDB를 이용한 시계열 데이터 저장, RESTful API를 통한 데이터 조회 및 관리 기능을 제공합니다.

## 시스템 구조

```
aton_server_msa/
├── mosquitto/          # MQTT Broker (Eclipse Mosquitto)
├── comm2center/        # MQTT 데이터 수신 및 InfluxDB 저장 서비스
├── restfulapi/         # Flask 기반 REST API 서버
└── docker-compose.yml  # Docker Compose 설정
```

### 주요 컴포넌트

1. **InfluxDB (1.8)** - 시계열 데이터베이스
   - 포트: 8086
   - IoT 센서 데이터 저장 및 관리

2. **Mosquitto** - MQTT 브로커
   - 포트: 31883
   - IoT 장비와의 실시간 통신

3. **comm2center** - 데이터 수집 서비스
   - MQTT 메시지를 구독하여 InfluxDB에 저장
   - Python 기반 서비스

4. **RESTful API** - 웹 API 서버
   - 포트: 5000
   - Flask 기반 REST API
   - 데이터 조회, 이미지 관리, MQTT 메시지 발행 등

## 요구사항

- Docker
- Docker Compose

## 설치 및 실행

### 1. 환경 변수 설정

`.env` 파일을 확인하고 필요시 수정합니다:

```bash
cd aton_server_msa
```

### 2. Docker Compose로 실행

```bash
docker-compose up -d
```

### 3. 서비스 확인

```bash
docker-compose ps
```

## 서비스 엔드포인트

- **RESTful API**: `http://localhost:5000`
- **InfluxDB**: `http://localhost:8086`
- **MQTT Broker**: `mqtt://localhost:31883`

## 개발 환경

- Python 3.x
- InfluxDB 1.8
- Mosquitto MQTT Broker
- Flask

## 주요 기능

- MQTT를 통한 실시간 IoT 데이터 수집
- InfluxDB를 이용한 시계열 데이터 저장
- RESTful API를 통한 데이터 조회 및 관리
- 이미지 업로드 및 관리
- MQTT 메시지 발행 기능

## 라이선스

Copyright 2021 - sycho (aton@2021)

## 문의

프로젝트 관련 문의사항은 이슈를 등록해주세요.
