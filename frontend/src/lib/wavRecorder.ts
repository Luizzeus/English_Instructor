/**
 * Records microphone audio and encodes it as 16 kHz / 16-bit / mono PCM WAV —
 * the format the backend's Azure Speech integration expects without needing
 * GStreamer to decode compressed browser formats server-side.
 *
 * Uses ScriptProcessorNode (deprecated but universally supported) rather than
 * AudioWorklet to avoid the extra module-loading complexity under Vite.
 */

const TARGET_SAMPLE_RATE = 16000

export class WavRecorder {
  private stream: MediaStream
  private audioContext: AudioContext
  private source: MediaStreamAudioSourceNode
  private processor: ScriptProcessorNode
  private chunks: Float32Array[] = []

  private constructor(
    stream: MediaStream,
    audioContext: AudioContext,
    source: MediaStreamAudioSourceNode,
    processor: ScriptProcessorNode,
  ) {
    this.stream = stream
    this.audioContext = audioContext
    this.source = source
    this.processor = processor
  }

  static async start(): Promise<WavRecorder> {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const audioContext = new AudioContext()
    const source = audioContext.createMediaStreamSource(stream)
    const processor = audioContext.createScriptProcessor(4096, 1, 1)

    const recorder = new WavRecorder(stream, audioContext, source, processor)
    processor.onaudioprocess = (event) => {
      recorder.chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
    }
    source.connect(processor)
    processor.connect(audioContext.destination)

    return recorder
  }

  async stop(): Promise<Blob> {
    this.processor.disconnect()
    this.source.disconnect()
    this.stream.getTracks().forEach((track) => track.stop())

    const merged = mergeChunks(this.chunks)
    const downsampled = downsample(merged, this.audioContext.sampleRate, TARGET_SAMPLE_RATE)
    const wavBuffer = encodeWav(downsampled, TARGET_SAMPLE_RATE)

    await this.audioContext.close()
    return new Blob([wavBuffer], { type: 'audio/wav' })
  }
}

function mergeChunks(chunks: Float32Array[]): Float32Array {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const result = new Float32Array(length)
  let offset = 0
  for (const chunk of chunks) {
    result.set(chunk, offset)
    offset += chunk.length
  }
  return result
}

function downsample(samples: Float32Array, inputRate: number, outputRate: number): Float32Array {
  if (outputRate === inputRate) return samples

  const ratio = inputRate / outputRate
  const newLength = Math.round(samples.length / ratio)
  const result = new Float32Array(newLength)

  for (let i = 0; i < newLength; i++) {
    const start = Math.floor(i * ratio)
    const end = Math.min(Math.floor((i + 1) * ratio), samples.length)
    let sum = 0
    let count = 0
    for (let j = start; j < end; j++) {
      sum += samples[j]
      count++
    }
    result[i] = count > 0 ? sum / count : 0
  }

  return result
}

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const bytesPerSample = 2
  const blockAlign = bytesPerSample // mono
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample)
  const view = new DataView(buffer)

  writeAsciiString(view, 0, 'RIFF')
  view.setUint32(4, 36 + samples.length * bytesPerSample, true)
  writeAsciiString(view, 8, 'WAVE')
  writeAsciiString(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM format
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true) // byte rate
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true) // bits per sample
  writeAsciiString(view, 36, 'data')
  view.setUint32(40, samples.length * bytesPerSample, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const clamped = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  }

  return buffer
}

function writeAsciiString(view: DataView, offset: number, text: string): void {
  for (let i = 0; i < text.length; i++) {
    view.setUint8(offset + i, text.charCodeAt(i))
  }
}
