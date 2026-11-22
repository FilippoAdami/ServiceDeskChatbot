import React from "react";

interface MarkdownMessageProps {
  content: string;
}

export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content }) => {
  // Parse code blocks vs regular text blocks
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-2 text-sm leading-relaxed text-foreground">
      {parts.map((part, index) => {
        if (part.startsWith("```") && part.endsWith("```")) {
          const lines = part.slice(3, -3).trim().split("\n");
          let language = "";
          let code = part.slice(3, -3).trim();
          if (lines.length > 1 && !lines[0].includes(" ")) {
            language = lines[0];
            code = lines.slice(1).join("\n");
          }
          return (
            <div key={index} className="my-2 overflow-x-auto rounded-lg bg-zinc-900 p-3 text-xs font-mono text-zinc-100 border border-zinc-800">
              {language && <div className="text-[10px] text-zinc-400 mb-1 uppercase">{language}</div>}
              <pre className="whitespace-pre">{code}</pre>
            </div>
          );
        }

        // Regular text block: split into paragraphs or list blocks
        const paragraphs = part.split(/\n\n+/);
        return paragraphs.map((para, pIdx) => {
          const lines = para.trim().split("\n");

          // Check if lines form a list
          const isBulletList = lines.length > 0 && lines.every((l) => /^\s*[-*•]\s+/.test(l));
          const isNumberedList = lines.length > 0 && lines.every((l) => /^\s*\d+\.\s+/.test(l));

          if (isBulletList) {
            return (
              <ul key={`${index}-${pIdx}`} className="list-disc list-inside space-y-1 my-1">
                {lines.map((line, lIdx) => (
                  <li key={lIdx}>{renderInline(line.replace(/^\s*[-*•]\s+/, ""))}</li>
                ))}
              </ul>
            );
          }

          if (isNumberedList) {
            return (
              <ol key={`${index}-${pIdx}`} className="list-decimal list-inside space-y-1 my-1">
                {lines.map((line, lIdx) => (
                  <li key={lIdx}>{renderInline(line.replace(/^\s*\d+\.\s+/, ""))}</li>
                ))}
              </ol>
            );
          }

          return (
            <p key={`${index}-${pIdx}`} className="whitespace-pre-line">
              {renderInline(para)}
            </p>
          );
        });
      })}
    </div>
  );
};

function renderInline(text: string): React.ReactNode[] {
  const tokens = text.split(/(\*\*.*?\*\*|`.*?`)/g);

  return tokens.map((token, idx) => {
    if (token.startsWith("**") && token.endsWith("**") && token.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-foreground">
          {token.slice(2, -2)}
        </strong>
      );
    }
    if (token.startsWith("`") && token.endsWith("`") && token.length >= 2) {
      return (
        <code
          key={idx}
          className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-primary"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    return token;
  });
}
