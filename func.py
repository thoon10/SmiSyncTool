from PyQt5.QtWidgets import QFileDialog
import re


def open_file_dialog(parent, title):
    fname, _ = QFileDialog.getOpenFileName(parent, title, '', 'SMI Files (*.smi);;All Files (*)')
    return fname

def select_save_path(parent, title):
    fname, _ = QFileDialog.getSaveFileName(parent, title, '', 'SMI Files (*.smi);;All Files (*)')
    return fname

def find_all_subtitle_occurrences(file_path, search_text):
    results = []
    if not search_text:
        return results

    try:
        with open(file_path, 'r', encoding='utf-16') as infile:
            for line in infile:
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

    try:
        with open(subtitle_file, 'r', encoding='utf-16') as infile, \
                open(save_file, 'w', encoding='utf-16') as outfile:

            for line in infile:
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

    try:
        with open(subtitle_file, 'r', encoding='utf-16') as infile, \
                open(save_file, 'w', encoding='utf-16') as outfile:

            for line in infile:
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
