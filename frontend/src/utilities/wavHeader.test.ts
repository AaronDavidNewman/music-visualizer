import { describe, expect, it } from "vitest";
import { readSampleRate } from "./wavHeader";

function ascii(text: string): number[] {
  return [...text].map((c) => c.charCodeAt(0));
}

function u32(n: number): number[] {
  return [n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >>> 24) & 255];
}

function u16(n: number): number[] {
  return [n & 255, (n >> 8) & 255];
}

function fmtChunk(sampleRate: number): number[] {
  // PCM, 2 channels, byte rate, block align, 16 bits
  return [...ascii("fmt "), ...u32(16), ...u16(1), ...u16(2), ...u32(sampleRate), ...u32(sampleRate * 4), ...u16(4), ...u16(16)];
}

function chunk(id: string, data: number[]): number[] {
  const padded = data.length % 2 ? [...data, 0] : data;
  return [...ascii(id), ...u32(data.length), ...padded];
}

function wav(form: string, chunks: number[][], extraBytes = 0): Blob {
  const body = [...ascii("WAVE"), ...chunks.flat()];
  const bytes = new Uint8Array([...ascii(form), ...u32(body.length + extraBytes), ...body, ...new Array(extraBytes).fill(0)]);
  return new Blob([bytes]);
}

describe("readSampleRate", () => {
  it.each([44100, 48000, 22050])("reads %d Hz when fmt comes first", async (rate) => {
    expect(await readSampleRate(wav("RIFF", [fmtChunk(rate)]))).toBe(rate);
  });

  it("skips chunks before fmt, including odd-sized ones", async () => {
    const file = wav("RIFF", [chunk("LIST", [1, 2, 3]), chunk("bext", new Array(602).fill(7)), fmtChunk(48000)]);
    expect(await readSampleRate(file)).toBe(48000);
  });

  it("reads RF64 files", async () => {
    expect(await readSampleRate(wav("RF64", [chunk("ds64", new Array(28).fill(0)), fmtChunk(96000)]))).toBe(96000);
  });

  it("works on a File as well as a Blob", async () => {
    const blob = wav("RIFF", [fmtChunk(44100)]);
    expect(await readSampleRate(new File([blob], "song.wav"))).toBe(44100);
  });

  it("only needs the start of a large file", async () => {
    expect(await readSampleRate(wav("RIFF", [fmtChunk(44100)], 1_000_000))).toBe(44100);
  });

  it("returns null for things that are not readable WAV headers", async () => {
    expect(await readSampleRate(new Blob([]))).toBeNull();
    expect(await readSampleRate(new Blob([new Uint8Array(ascii("hello world, not audio"))]))).toBeNull();
    expect(await readSampleRate(new Blob([new Uint8Array([...ascii("RIFF"), ...u32(4), ...ascii("WAVE")])]))).toBeNull();
    expect(await readSampleRate(wav("RIFX", [fmtChunk(44100)]))).toBeNull();
    expect(await readSampleRate(wav("RIFF", [chunk("data", new Array(100).fill(0))]))).toBeNull();
  });

  it("returns null for a truncated fmt chunk", async () => {
    const whole = new Uint8Array(await wav("RIFF", [fmtChunk(44100)]).arrayBuffer());
    expect(await readSampleRate(new Blob([whole.slice(0, 22)]))).toBeNull();
  });

  it("returns null when fmt lies beyond the first 64 KB", async () => {
    const file = wav("RIFF", [chunk("junk", new Array(70000).fill(0)), fmtChunk(44100)]);
    expect(await readSampleRate(file)).toBeNull();
  });

  it("returns null for a zero sample rate", async () => {
    expect(await readSampleRate(wav("RIFF", [fmtChunk(0)]))).toBeNull();
  });
});
