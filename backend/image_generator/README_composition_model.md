구도모델(ControlNet) 적용 실험 기록
0. 실험 목표

누끼 이미지와 레퍼런스를 합성한 완성 이미지에 구도모델을 적용하여,
단순 합성 단계에서 남아 있는 이질감, 경계 부자연스러움, 조명 차이, 그림자 표현을 개선할 수 있는지 확인하였다.

1. 사용 모델 및 파이프라인
Base Model: SG161222/RealVisXL_V5.0
ControlNet: diffusers/controlnet-canny-sdxl-1.0
Pipeline: StableDiffusionXLControlNetImg2ImgPipeline
선택 기준
실사 음식 이미지에 적합
기존 합성 구도를 유지
경계, 조명, 그림자 자연스럽게 보정 가능
RTX 4070 Ti SUPER (VRAM 16GB) 환경에서 실행 가능
2. 1차 실험 (Batch 처리)
사용 파일

test_composition_refine_controlnet.py

처리 방식
합성 이미지 → 1024x1024 resize
Canny Edge 생성
ControlNet img2img 적용
여러 장을 for문으로 한 번에 처리
주요 설정
strength = 0.25
controlnet_conditioning_scale = 0.45
num_inference_steps = 30
guidance_scale = 6.0
height = 1024
width = 1024
실행 결과
결과 이미지는 정상 생성됨
음식과 배경의 색감 및 경계 일부 개선됨
문제점
장당 5분 이상 소요
모델 초기 로딩 + 캐시 생성으로 시간 증가
GPU VRAM 약 15GB 이상 사용
WSL vmmem 메모리 증가
반복 실험 비효율
3. 2차 실험 (One-by-One 방식)
사용 파일

test_composition_refine_controlnet_one_by_one.py

변경 목적
처리 속도 개선
메모리 사용량 안정화
주요 변경점
한 장 처리 후 메모리 정리
del image
torch.cuda.empty_cache()
gc.collect()
해상도 변경
1024 → 768
주요 설정
strength = 0.30
controlnet_conditioning_scale = 0.42
num_inference_steps = 16
guidance_scale = 5.8
height = 768
width = 768
결과
처리 속도: 약 20초 미만 / 장
1차 대비 크게 개선됨
품질 변화
음식과 배경 색감 자연스럽게 통일
접시와 음식 경계 부드러워짐
전체 이미지가 하나의 사진처럼 정리됨
디테일 손상 거의 없음
4. 케이크 케이스 실험
4-1. 1회차 (원본 합성 이미지)

파일: cake_on_4_bg.png

상태
누끼 + 레퍼런스 합성 결과
관찰
전체 구도는 안정적
음식 배치도 자연스러운 편
약간의 합성 느낌 존재
조명 톤 불일치
경계가 완전히 자연스럽지는 않음
4-2. 2회차 (중간 강도 적용)

파일: cake_on_4_bg__controlnet_refined_mid.png

설정
strength = 0.30
controlnet_conditioning_scale = 0.42
num_inference_steps = 16
guidance_scale = 5.8
결과
색감 통일됨
경계 자연스러워짐
배경과 음식 일체감 증가
합성 느낌 감소
디테일 유지
평가

→ 가장 안정적이고 자연스러운 결과

4-3. 3회차 (강도 증가)

파일: cake_on_4_bg__controlnet_refined_stronger.png

변경 설정
strength = 0.36
controlnet_conditioning_scale = 0.46
num_inference_steps = 20
guidance_scale = 6.0
목적
접촉감 강화
그림자 표현 개선
경계 추가 자연화
결과
전체 이미지 재해석 강해짐
접시와 배경 연결은 자연스러움
음식 전체가 흐릿해짐
과보정 느낌 발생
평가

→ 강도 과다로 품질 저하 발생

5. 최종 결론
최종 채택

cake_on_4_bg__controlnet_refined_mid.png

이유
구도 유지
자연스러운 색감 및 경계
디테일 유지
과보정 없음
6. 핵심 인사이트
ControlNet Canny는 구도 변경용이 아닌 후보정용
적절한 strength에서
조명
경계
질감
개선 효과 있음
과도한 strength는
블러 증가
디테일 손실
부자연스러움 발생
7. 결론 요약
Batch 처리 → 비효율 (시간/메모리 문제)
One-by-One → 최적
중간 강도 → 최적 품질
강한 보정 → 오히려 역효과