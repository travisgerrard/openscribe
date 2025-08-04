/**
 * Text Processing Utilities
 *
 * Utility functions for processing and formatting streaming text content,
 * handling chunk concatenation, deduplication, and formatting.
 */

/**
 * Append a streaming chunk to an existing buffer.
 *
 * Rules:
 *   • If either side already ends/starts with whitespace → just concatenate.
 *   • Do **not** inject a space between:
 *       – a digit followed by another digit  (splits like "2","1" → "21")
 *       – a hyphen boundary (e.g. "21", "-year" → "21-year")
 *       – any punctuation that normally glues to the previous token
 *         (comma, period, semicolon, colon, slash).
 *   • Otherwise insert a single space.
 */
export function appendChunk(buffer, chunk) {
  if (!chunk) return buffer;

  const lastChar = buffer.slice(-1);
  const firstChar = chunk.charAt(0);

  const noSpaceNeeded =
        // existing whitespace at joint
        /\s/.test(lastChar) || /^\s/.test(chunk) ||
        // digit followed by digit → same number
        (/\d/.test(lastChar) && /^\d$/.test(firstChar)) ||
        // keep hyphenated tokens together
        firstChar === '-' || lastChar === '-' ||
        // punctuation that glues
        /[.,;:/()]/.test(firstChar) ||
        // Mid‑word split: both sides are letters => likely same word
        (/[a-zA-Z]/.test(lastChar) && /^[a-zA-Z]$/.test(firstChar));

  if (!noSpaceNeeded) {
    buffer += ' ';
  }
  return buffer + chunk;
}

/**
 * Normalise raw response text so that our formatter can reliably detect
 * bullet lines. Improved version:
 *   1) Collapse runs of whitespace.
 *   2) If a dash surrounded by spaces appears, treat it as a bullet break (" - " → "\n- ").
 *   3) Put a newline in front of a dash that starts a new list after a period.
 */
export function normaliseResponse(text) {
  if (!text) return '';

  // 1) Collapse runs of whitespace.
  text = text.replace(/\s+/g, ' ').trim();

  // 2) If a dash surrounded by spaces appears, treat it as a bullet break:
  //    " - " → "\n- "
  text = text.replace(/\s-\s+/g, '\n- ');

  // 3) Put a newline in front of a dash that starts a new list after a period.
  text = text.replace(/(?:^|\.)\s*-\s+/g, match =>
    match.startsWith('.') ? '.\n- ' : '- '
  );

  return text;
}

/**
 * Remove simple duplicated "word-word" patterns that arise from chunk
 * boundaries, e.g. "year-year" or "old-old".
 */
export function deduplicateHyphenPairs(text) {
  return text.replace(/\b(\w+)-\1\b/gi, '$1');
}

/**
 * Collapse *double* duplicate tokens separated by a space, e.g.
 *   "year year"  → "year"
 *   "old old"    → "old"
 */
export function deduplicateWordPairs(text) {
  return text.replace(/\b(\w+)\s+\1\b/gi, '$1');
}

/**
 * Parse and separate thinking and response content from LLM output
 */
export function parseThinkingAndResponse(text) {
  if (!text) return { thinking: '', response: '' };

  // Extract content between <think> tags
  const thinkMatch = text.match(/<think>([\s\S]*?)<\/think>/i);
  const thinkingContent = thinkMatch ? thinkMatch[1].trim() : '';

  // Remove thinking content to get response
  let responseContent = text.replace(/<think>[\s\S]*?<\/think>/i, '').trim();

  // Clean up any remaining HTML tags or artifacts
  responseContent = responseContent.replace(/<[^>]*>/g, '').trim();

  return {
    thinking: formatThinkingContent(thinkingContent),
    response: formatResponseContent(responseContent)
  };
}

/**
 * Format thinking content with tidy paragraphs
 */
export function formatThinkingContent(text) {
  if (!text) return '';

  // 1) Collapse whitespace runs to a single space
  text = text.replace(/\s+/g, ' ').trim();

  // 2) Heuristic: insert a newline after sentence‑ending punctuation
  //    followed by a capital letter (start of next sentence).
  text = text.replace(/([.!?])\s+(?=[A-Z])/g, '$1\n');

  // 3) Now split on those newlines
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length)
    .map(line => `<p>${line}</p>`)
    .join('');
}

/**
 * Format response content with bullet points
 */
export function formatResponseContent(text) {
  if (!text) return '';

  // Handle bullet points
  if (text.startsWith('-')) {
    const items = text.split('\n')
      .map(line => line.trim())
      .filter(line => line.startsWith('-'))
      .map(line => line.replace(/^-\s*/, '').trim())
      .filter(item => item.length > 0);

    if (items.length > 0) {
      return `<ul>${items.map(item => `<li>${item}</li>`).join('')}</ul>`;
    }
  }

  // Regular paragraph
  return `<p>${text.replace(/\n/g, ' ').trim()}</p>`;
}