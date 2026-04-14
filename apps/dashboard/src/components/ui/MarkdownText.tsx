"use client";

import React from "react";

// ── Inline renderer ────────────────────────────────────────────────────────
// Handles: `code`, **bold**, *italic*, ***bold-italic***

function renderInline(text: string): React.ReactNode[] {
  // Split on inline-code spans first so we don't process markup inside them
  const codeParts = text.split(/(`[^`\n]+`)/g);

  return codeParts.flatMap((part, ci) => {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code
          key={`c${ci}`}
          className="px-1 py-0.5 bg-zinc-800 text-sky-300 rounded text-[0.8em] font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold-italic, bold, italic
    const emphParts = part.split(/(\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|\*[^*\n]+\*)/g);
    return emphParts.map((seg, ei) => {
      if (seg.startsWith("***") && seg.endsWith("***") && seg.length > 6) {
        return <strong key={`${ci}-${ei}`}><em>{seg.slice(3, -3)}</em></strong>;
      }
      if (seg.startsWith("**") && seg.endsWith("**") && seg.length > 4) {
        return <strong key={`${ci}-${ei}`}>{seg.slice(2, -2)}</strong>;
      }
      if (seg.startsWith("*") && seg.endsWith("*") && seg.length > 2) {
        return <em key={`${ci}-${ei}`}>{seg.slice(1, -1)}</em>;
      }
      return <React.Fragment key={`${ci}-${ei}`}>{seg}</React.Fragment>;
    });
  });
}

// ── Block tokeniser ────────────────────────────────────────────────────────

type Block =
  | { type: "code_block"; lang: string; content: string }
  | { type: "heading"; level: 1 | 2 | 3; content: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "paragraph"; content: string };

function tokenise(md: string): Block[] {
  const lines = md.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    const fenceMatch = line.match(/^```(\w*)/);
    if (fenceMatch) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      blocks.push({ type: "code_block", lang: fenceMatch[1], content: codeLines.join("\n") });
      i++; // skip closing ```
      continue;
    }

    // ATX heading
    const headingMatch = line.match(/^(#{1,3}) (.+)/);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: Math.min(headingMatch[1].length, 3) as 1 | 2 | 3,
        content: headingMatch[2],
      });
      i++;
      continue;
    }

    // Unordered list
    if (/^[-*] /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*] /.test(lines[i])) {
        items.push(lines[i].replace(/^[-*] /, ""));
        i++;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    // Ordered list
    if (/^\d+\. /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ""));
        i++;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    // Blank line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph: collect until blank line or a block-level marker
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,3} |[-*] |\d+\. |```)/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length) {
      blocks.push({ type: "paragraph", content: paraLines.join(" ") });
    }
  }

  return blocks;
}

// ── Component ──────────────────────────────────────────────────────────────

const HEADING_CLS: Record<1 | 2 | 3, string> = {
  1: "text-base font-semibold text-zinc-100 mt-1",
  2: "text-sm font-semibold text-zinc-100",
  3: "text-sm font-medium text-zinc-200",
};

export function MarkdownText({ children, streaming }: { children: string; streaming?: boolean }) {
  const blocks = tokenise(children);

  return (
    <div className="space-y-2.5">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "code_block":
            return (
              <pre
                key={i}
                className="bg-zinc-950 border border-zinc-800 rounded p-3 text-xs text-zinc-300 font-mono overflow-x-auto leading-relaxed"
              >
                <code>{block.content}</code>
              </pre>
            );

          case "heading": {
            const Tag = `h${block.level}` as "h1" | "h2" | "h3";
            return (
              <Tag key={i} className={HEADING_CLS[block.level]}>
                {renderInline(block.content)}
              </Tag>
            );
          }

          case "ul":
            return (
              <ul key={i} className="list-disc list-outside ml-4 space-y-1">
                {block.items.map((item, j) => (
                  <li key={j} className="text-sm text-zinc-200 leading-relaxed">
                    {renderInline(item)}
                  </li>
                ))}
              </ul>
            );

          case "ol":
            return (
              <ol key={i} className="list-decimal list-outside ml-4 space-y-1">
                {block.items.map((item, j) => (
                  <li key={j} className="text-sm text-zinc-200 leading-relaxed">
                    {renderInline(item)}
                  </li>
                ))}
              </ol>
            );

          default:
            return (
              <p key={i} className="text-sm text-zinc-200 leading-relaxed">
                {renderInline(block.content)}
                {streaming && i === blocks.length - 1 && (
                  <span className="inline-block w-2 h-4 ml-0.5 bg-sky-400 animate-pulse align-middle" />
                )}
              </p>
            );
        }
      })}
      {/* cursor when the last block is not a paragraph (e.g. still building a list) */}
      {streaming && blocks.length > 0 && blocks[blocks.length - 1].type !== "paragraph" && (
        <span className="inline-block w-2 h-4 bg-sky-400 animate-pulse align-middle" />
      )}
    </div>
  );
}
