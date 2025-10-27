from PyQt5.QtWidgets import QFileDialog
import re


def open_file_dialog(parent, title):
    # QFileDialog.getOpenFileName(부모 위젯, 창 제목, 기본 경로, 파일 필터)
    fname, _ = QFileDialog.getOpenFileName(parent, title, '', 'SMI Files (*.smi);;All Files (*)')
    return fname

def select_save_path(parent, title):
    # QFileDialog.getSaveFileName(부모 위젯, 창 제목, 기본 경로, 파일 필터)
    fname, _ = QFileDialog.getSaveFileName(parent, title, '', 'SMI Files (*.smi);;All Files (*)')
    return fname


def read_file_auto_encoding(file_path):
    # 1. utf-16 (BOM이 있는 유니코드 파일)
    # 2. utf-8-sig (BOM이 있는 utf-8 파일)
    # 3. cp949 (ANSI/EUC-KR 한글 윈도우 기본)
    encodings_to_try = ['utf-16', 'utf-8-sig', 'cp949']

    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            # 성공 시, 파일 내용과 사용된 인코딩을 반환
            print(f"  - 파일 인코딩 감지 성공: {enc}")
            return content, enc
        except UnicodeDecodeError:
            continue  # 다음 인코딩 시도
        except Exception as e:
            print(f"[오류] 파일을 읽는 중 예외 발생 (인코딩: {enc}): {e}")
            return None, None  # 그 외 오류

    # 모든 인코딩 시도 실패
    print(f"[오류] '{file_path}'의 인코딩을 감지할 수 없습니다. (지원되지 않는 형식)")
    return None, None

def find_all_subtitle_occurrences(file_path, search_text):
    """
    SMI 파일에서 특정 텍스트가 포함된 모든 라인을 찾아
    [ {'ms': 시간_ms, 'text': 전체_자막_내용}, ... ] 리스트 형태로 반환합니다.
    """
    results = []
    if not search_text:
        return results

    # 1. 헬퍼 함수로 파일 읽기
    content, _ = read_file_auto_encoding(file_path)  # 인코딩 이름은 필요 없음
    if content is None:
        return results  # 읽기 실패

    try:
        # 2. 파일이 아닌 메모리의 content를 한 줄씩 처리
        for line in content.splitlines():  # 여기선 keepends=True 불필요
            if 'class=krcc' in line.lower() and search_text in line:
                match = re.search(r'<Sync Start=(\d+)>', line, re.IGNORECASE)
                if match:
                    timestamp_ms = int(match.group(1))
                    clean_line = re.sub(r'<.*?>', '', line).strip()
                    if clean_line:
                        results.append({'ms': timestamp_ms, 'text': clean_line})
    except Exception as e:
        print(f"[오류] 자막 검색 중 문제 발생: {e}")

    return results

def run_batch_adjustment(subtitle_file, save_file, time_offset):
    print("=== 전체 싱크 일괄 조절 시작 ===")
    print(f"  - 원본 파일: {subtitle_file}")
    print(f"  - 저장 파일: {save_file}")
    print(f"  - 조절 시간: {time_offset}초")

    try:
        offset_ms = int(float(time_offset) * 1000)
    except ValueError:
        print("[오류] 조절 시간이 올바른 숫자가 아닙니다.")
        return False

        # 1. 헬퍼 함수로 파일 읽기
    content, detected_encoding = read_file_auto_encoding(subtitle_file)
    if content is None:
        return False  # 읽기 실패


    try:
        # 2. 감지된 인코딩으로 저장 파일 열기
        with open(save_file, 'w', encoding=detected_encoding) as outfile:
            # 3. 파일이 아닌 메모리의 content를 한 줄씩 처리
            for line in content.splitlines(keepends=True):
                match = re.search(r'<Sync Start=(\d+)>', line, re.IGNORECASE)

                if match:
                    original_ms_str = match.group(1)
                    original_ms = int(original_ms_str)
                    new_ms = original_ms + offset_ms

                    if new_ms < 0:
                        new_ms = 0

                    new_line = line.replace(f'Start={original_ms_str}', f'Start={new_ms}')
                    outfile.write(new_line)
                else:
                    outfile.write(line)

    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {subtitle_file}")
        return False
    except UnicodeDecodeError:
        print("[오류] 'utf-8' 인코딩으로 파일을 읽을 수 없습니다.")
        print("       파일이 'cp949(한글)' 또는 'utf-8'일 수 있습니다.")
        return False
    except Exception as e:
        print(f"[오류] 파일 처리 중 문제가 발생했습니다: {e}")
        return False

    print("작업 완료!")
    return True

def run_specific_adjustment(subtitle_file, save_file, selected_sync_ms, target_time_str):
    print("=== 특정 자막 기준 싱크 조절 시작 ===")
    print(f"  - 원본 파일: {subtitle_file}")
    print(f"  - 저장 파일: {save_file}")
    print(f"  - 기준 자막의 원래 시간: {selected_sync_ms} ms")
    print(f"  - 목표 시간: {target_time_str}초")

    try:
        # 1. 목표 시간을 ms로 변환
        target_ms = int(float(target_time_str) * 1000)
        # 2. 조절할 시간 차이(offset) 계산
        offset_ms = target_ms - selected_sync_ms
    except ValueError:
        print("[오류] 목표 시간이 올바른 숫자가 아닙니다.")
        return False

    print(f"  - 계산된 시간 차이(offset): {offset_ms} ms")

    # 1. 헬퍼 함수로 파일 읽기
    content, detected_encoding = read_file_auto_encoding(subtitle_file)
    if content is None:
        return False  # 읽기 실패

    try:
        # 2. 감지된 인코딩으로 저장 파일 열기
        with open(save_file, 'w', encoding=detected_encoding) as outfile:
            # 3. 파일이 아닌 메모리의 content를 한 줄씩 처리
            for line in content.splitlines(keepends=True):
                match = re.search(r'<Sync Start=(\d+)>', line, re.IGNORECASE)

                if match:
                    original_ms = int(match.group(1))
                    # 3. 모든 자막에 동일한 offset을 적용
                    new_ms = original_ms + offset_ms

                    if new_ms < 0:
                        new_ms = 0

                    new_line = line.replace(f'Start={original_ms}', f'Start={new_ms}')
                    outfile.write(new_line)
                else:
                    outfile.write(line)

    except Exception as e:
        print(f"[오류] 파일 처리 중 문제가 발생했습니다: {e}")
        return False

    print("작업 완료!")
    return True
