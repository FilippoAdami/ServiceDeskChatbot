import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Mock scrollIntoView in JSDOM
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// Runs a cleanup after each test case
afterEach(() => {
  cleanup();
});
