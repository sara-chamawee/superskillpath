import { marked } from 'marked';

export function renderMarkdown(text) {
  try { return marked.parse(text || ''); }
  catch { return text || ''; }
}
