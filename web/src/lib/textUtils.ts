const VOWELS = "aeiouáéíóúâêôãõàüy";

function stripPunctuationEdges(input: string): string {
  // Remove pontuação nas bordas (mantém conteúdo interno)
  return input.replace(/^[\W_]+|[\W_]+$/g, "");
}

export function isMonosyllabic(rawWord: string): boolean {
  const word = stripPunctuationEdges(rawWord.toLowerCase());
  if (!word) return false;
  if (word.length <= 2) return true;

  // Conta grupos de vogais como aproximação de sílabas
  const matches = word.match(new RegExp("[" + VOWELS + "]+", "gi"));
  const syllables = matches ? matches.length : 0;
  return syllables <= 1;
}

export function groupMonosyllablesWithNext(words: string[]): string[] {
  const tokens: string[] = [];
  let i = 0;
  while (i < words.length) {
    const current = words[i];
    const next = i + 1 < words.length ? words[i + 1] : null;
    if (isMonosyllabic(current) && next) {
      tokens.push(`${current} ${next}`);
      i += 2;
    } else {
      tokens.push(current);
      i += 1;
    }
  }
  return tokens;
}

export function countWordsInToken(token: string): number {
  return token.trim().split(/\s+/).filter(Boolean).length;
}

export function endPunctuationMultiplier(token: string): number {
  const t = token.trim();
  if (/\.\.\.$/.test(t)) return 2.5; // reticências
  if (/[.!?]$/.test(t)) return 2.0; // fim de frase
  if (/[;:]$/.test(t)) return 1.75; // pausa média
  if (/,$/.test(t)) return 1.5; // vírgula
  return 1.0;
}

export function complexityMultiplier(token: string): number {
  const clean = token.replace(/[^\p{L}\p{N}]+/gu, "");
  const length = clean.length;
  if (length <= 3) return 0.9;
  if (length <= 6) return 1.0;
  if (length <= 10) return 1.2;
  return 1.5;
}


