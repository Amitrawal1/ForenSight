// Decorative scatter of dots, small squares and × marks on a 32px grid.
// Each letter below is one grid cell, so the shape is easy to edit by hand:
//   o = white dot, s = pale square, x = teal ×, t = teal dot, . = empty
// "wide" fills the empty space beside the wordmark on big screens. "small" sits beside the statement on phones.
const LAYOUTS = {
  wide: [
    "....s.o.......o.o.....x.....o.o.s.",
    "..s...o.t...o.o.o...o.o.........s.",
    "......o.o.x.....s.......o.t.x.o...",
    "..o.o.o.....o.o.o.x...s.s.....o...",
    "..s.s...x.o.o.....t.o.s.....o.....",
  ],
  small: ["..s.o.x.....", "s.o.o...t.o.", "..x...o.s..."],
};

const CELL = 32;

export default function MarkPattern({ layout = "wide", className = "" }) {
  const ROWS = LAYOUTS[layout];
  const marks = [];
  ROWS.forEach((row, r) => {
    [...row].forEach((kind, c) => {
      const x = c * (CELL / 2) + 12;
      const y = r * CELL + 12;
      const key = `${r}-${c}`;
      if (kind === "o") marks.push(<circle key={key} cx={x} cy={y} r="10" fill="#FFFFFF" />);
      if (kind === "t") marks.push(<circle key={key} cx={x} cy={y} r="7" fill="#0E6E8C" />);
      if (kind === "s") marks.push(<rect key={key} x={x - 10} y={y - 10} width="20" height="20" rx="1" fill="#D9E1E7" />);
      if (kind === "x")
        marks.push(<path key={key} d={`M${x - 7} ${y - 7}L${x + 7} ${y + 7}M${x + 7} ${y - 7}L${x - 7} ${y + 7}`} stroke="#0E6E8C" strokeWidth="3.5" strokeLinecap="round" />);
    });
  });

  return (
    <svg viewBox={`0 0 ${(ROWS[0].length * CELL) / 2} ${ROWS.length * CELL}`} className={className} aria-hidden="true">
      {marks}
    </svg>
  );
}
