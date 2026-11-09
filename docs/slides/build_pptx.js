// Build DeadDrops-slides.pptx from slide PNGs (rendered from DeadDrops-slides.pdf), with speaker notes.
//   pdftoppm -scale-to-x 1920 -scale-to-y 1080 -png DeadDrops-slides.pdf IMGDIR/hi
//   NODE_PATH=<dir with pptxgenjs> node build_pptx.js IMGDIR
const pptxgen = require("pptxgenjs");
const path = require("path");

const NOTES = [
  "We study oversight of agent swarms that coordinate only through a shared folder. 247 episodes, three model families. The headline: once attackers learned why they were caught, 10 of 10 attacks went undetected.",
  "A shared folder is a channel nobody designed. The hard part is that honest teamwork moves the same information, so we built a control: covert and honest prompts differ by one sentence.",
  "Four agents, each holding one fragment of a deploy token. Covert teams assemble it without drawing attention; the honest control assembles it openly. We score LLM judges and file-level monitors by AUROC and undetected success at a 5% audit budget.",
  "First failure: monitors that track information flow. Provenance is below chance on every model, because honest teams cooperate more openly. Without the honest control these monitors would look useful.",
  "Monitors that look for hiding do work against naive colluders: the judge reaches 0.85 to 1.00 and a hidden-file rule caught 6 of 6 fresh covert teams with no false alarms. The strongest model even recruited its teammates by editing the shared migration guide.",
  "Then we briefed the attackers on what the judge looks for and why they were flagged. They stopped hiding: no hidden files, open and accurate notes. The judge fell to chance and in round 3 every attack succeeded undetected.",
  "Why? Log edits and an honest 'vault' team show the monitors detect unexplained concealment. File rules flag every honest vault team. A judge told the security policy separates collusion from legitimate hiding as well as from open teamwork.",
  "So once colluders stop hiding, only one question separates them from honest teams: was the outcome allowed? Check outcomes against policy, give the judge the policy, treat file rules as a first layer, and always test against honest teamwork and an informed attacker.",
  "Everything is open: code, pre-registration, every episode log and judge score, and the tripwire tool that replays an episode with alerts. Thank you.",
];

const dir = process.argv[2];
const pptx = new pptxgen();
pptx.layout = "LAYOUT_16x9";
pptx.title = "When Colluders Stop Hiding";
NOTES.forEach((note, i) => {
  const s = pptx.addSlide();
  s.addImage({ path: path.join(dir, `hi-${i + 1}.png`), x: 0, y: 0, w: 10, h: 5.625 });
  s.addNotes(note);
});
pptx.writeFile({ fileName: path.join(__dirname, "DeadDrops-slides.pptx") }).then((f) => console.log("wrote", f));
