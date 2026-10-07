// Reads a WAV file's sample rate from its header, so the form can compute the default window spacing
// before anything is uploaded. Only the first 64 KB are read.

const HEADER_BYTES = 64 * 1024;

function tag(view: DataView, offset: number): string {
  return String.fromCharCode(
    view.getUint8(offset),
    view.getUint8(offset + 1),
    view.getUint8(offset + 2),
    view.getUint8(offset + 3),
  );
}

/** The file's sample rate in Hz, or null if it is not a WAV (RIFF or RF64) file whose `fmt ` chunk can be found. */
export async function readSampleRate(file: Blob): Promise<number | null> {
  try {
    const view = new DataView(await file.slice(0, HEADER_BYTES).arrayBuffer());
    if (view.byteLength < 12) return null;
    const form = tag(view, 0);
    if ((form !== "RIFF" && form !== "RF64") || tag(view, 8) !== "WAVE") return null;

    let pos = 12;
    while (pos + 8 <= view.byteLength) {
      const size = view.getUint32(pos + 4, true);
      if (tag(view, pos) === "fmt ") {
        if (pos + 16 > view.byteLength) return null;
        const rate = view.getUint32(pos + 12, true);
        return rate > 0 ? rate : null;
      }
      pos += 8 + size + (size % 2);
    }
    return null;
  } catch {
    return null;
  }
}
