let utterance = null;

export function speak(text, onEnd) {
  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    return false;
  }
  utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'th-TH';
  utterance.rate = 1.25;
  utterance.pitch = 1.8;
  const voices = window.speechSynthesis.getVoices();
  const thVoice = voices.find(v => v.lang.startsWith('th'));
  if (thVoice) utterance.voice = thVoice;
  if (onEnd) utterance.onend = onEnd;
  window.speechSynthesis.speak(utterance);
  return true;
}

// Preload voices
if (typeof window !== 'undefined') window.speechSynthesis?.getVoices();
