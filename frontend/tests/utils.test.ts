import { describe, it, expect } from "vitest";
import { formatBytes, formatDuration, cn } from "@/lib/utils";

describe("formatBytes", () => {
  it("formats bytes", () => expect(formatBytes(512)).toBe("512 B"));
  it("formats kilobytes", () => expect(formatBytes(2048)).toBe("2.0 KB"));
  it("formats megabytes", () => expect(formatBytes(1048576)).toBe("1.0 MB"));
});

describe("formatDuration", () => {
  it("formats sub-minute", () => expect(formatDuration(45)).toBe("45.0s"));
  it("formats minutes", () => expect(formatDuration(90)).toBe("1m 30s"));
});

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });
  it("handles conditional classes", () => {
    expect(cn("base", false && "no", "yes")).toBe("base yes");
  });
});
