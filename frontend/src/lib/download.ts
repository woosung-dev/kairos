/**
 * Blob 데이터를 파일로 다운로드하는 유틸리티.
 * 임시 <a> 태그를 생성하여 브라우저 다운로드를 트리거한다.
 */
export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
