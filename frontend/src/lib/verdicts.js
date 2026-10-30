// How each verdict looks. Red, amber and green are used only here, to carry the verdict's meaning.
// tone: classes for a verdict pill. The text is navy on a pale tint because white text
// on the amber colour is too faint to read (about 4.2:1, and we need 4.5:1).
// bar: class for a solid bar or dot. color: the same colour as a hex value.
export const VERDICTS = {
  likely_authentic: {
    label: "Likely Authentic",
    tone: "bg-verdict-authentic/10 border-verdict-authentic text-navy",
    bar: "bg-verdict-authentic",
    color: "#1F7A5C",
  },
  ai_generated: {
    label: "AI-Generated",
    tone: "bg-verdict-ai/10 border-verdict-ai text-navy",
    bar: "bg-verdict-ai",
    color: "#B4233C",
  },
  manipulated: {
    label: "Manipulated",
    tone: "bg-verdict-manipulated/10 border-verdict-manipulated text-navy",
    bar: "bg-verdict-manipulated",
    color: "#B4690E",
  },
  inconclusive: {
    label: "Inconclusive",
    tone: "bg-verdict-inconclusive/10 border-verdict-inconclusive text-navy",
    bar: "bg-verdict-inconclusive",
    color: "#4A5568",
  },
};
