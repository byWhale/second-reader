type PreviewReaction = {
  reaction_id: number;
  type: string;
  section_ref: string;
  anchor_quote: string;
  content: string;
};

type ChapterSection = {
  section_ref: string;
  reactions: PreviewReaction[];
};

type ChapterDetail = {
  chapter_id: number;
  chapter_ref: string;
  title: string;
  featured_reactions: PreviewReaction[];
  sections: ChapterSection[];
};

type BookDetail = {
  book_id: number;
  title: string;
  author: string;
};

function parseArgs(argv: string[]) {
  const args = new Map<string, string>();

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      continue;
    }
    const [rawKey, inlineValue] = token.slice(2).split("=", 2);
    const nextValue = inlineValue ?? argv[index + 1];
    if (!inlineValue) {
      index += 1;
    }
    args.set(rawKey, nextValue);
  }

  const bookId = Number(args.get("book-id"));
  const chapterId = Number(args.get("chapter-id"));
  const baseUrl = (args.get("base-url") || process.env["VITE_API_BASE_URL"] || "http://localhost:8000").replace(/\/+$/, "");

  if (!Number.isInteger(bookId) || !Number.isInteger(chapterId)) {
    throw new Error("Usage: npm run preview-reactions -- --book-id <bookId> --chapter-id <chapterId> [--base-url http://localhost:8000]");
  }

  return { bookId, chapterId, baseUrl };
}

async function requestJson<T>(baseUrl: string, path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    throw new Error(
      `Could not reach ${baseUrl}${path}. Start the backend first, or pass --base-url to a reachable API.\n${error instanceof Error ? error.message : String(error)}`,
    );
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Request failed for ${path}: ${response.status} ${response.statusText}${body ? `\n${body}` : ""}`);
  }

  return (await response.json()) as T;
}

function collectUniqueReactions(chapter: ChapterDetail): PreviewReaction[] {
  const reactions = new Map<number, PreviewReaction>();

  for (const reaction of chapter.featured_reactions) {
    reactions.set(reaction.reaction_id, reaction);
  }

  for (const section of chapter.sections) {
    for (const reaction of section.reactions) {
      if (!reactions.has(reaction.reaction_id)) {
        reactions.set(reaction.reaction_id, reaction);
      }
    }
  }

  return Array.from(reactions.values());
}

function previewLine(text: string, limit = 110) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit - 1)}…`;
}

async function main() {
  const { bookId, chapterId, baseUrl } = parseArgs(process.argv.slice(2));

  const [book, chapter] = await Promise.all([
    requestJson<BookDetail>(baseUrl, `/api/books/${bookId}`),
    requestJson<ChapterDetail>(baseUrl, `/api/books/${bookId}/chapters/${chapterId}`),
  ]);

  const reactions = collectUniqueReactions(chapter);

  if (reactions.length === 0) {
    console.log(`No reactions found for book ${bookId}, chapter ${chapterId}.`);
    return;
  }

  console.log(`${book.title} by ${book.author}`);
  console.log(`${chapter.chapter_ref} — ${chapter.title}`);
  console.log("");
  console.log("Paste into LANDING_PREVIEW_CONFIG.api.selectedReactionIds:");
  console.log(`[${reactions.map((reaction) => reaction.reaction_id).join(", ")}]`);
  console.log("");

  for (const reaction of reactions) {
    console.log(`${reaction.reaction_id} | ${reaction.type} | ${reaction.section_ref} | ${previewLine(reaction.anchor_quote)}`);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
