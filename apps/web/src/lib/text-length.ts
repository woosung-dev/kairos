// 글자 수 = 유니코드 코드 포인트 수 (BE Pydantic min_length/max_length 와 같은 기준)
//
// ★`String.prototype.length` 는 UTF-16 코드 유닛을 센다. 😀 같은 BMP 밖 문자는 2 로 세어져
//   FE 는 "50자" 로 통과시키고 BE(Python `len`) 는 25자로 보아 422 를 돌려준다 (C-025).
//   HTML `maxLength` 속성도 코드 유닛 기준이라 같은 불일치가 반대 방향으로 난다.
//   BE 한도를 흉내 내는 FE 검증은 반드시 이 함수로 센다.

/** 코드 포인트 기준 글자 수. */
export function codePointLength(value: string): number {
  return Array.from(value).length;
}
