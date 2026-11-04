// Decode, downmix and resample browser recordings to documented mono 24kHz PCM WAV.
export async function recordingToWav(blob) {
  const decoder = new AudioContext();
  let buffer;
  try {buffer = await decoder.decodeAudioData(await blob.arrayBuffer())} finally {await decoder.close()}
  const offline = new OfflineAudioContext(1, Math.ceil(buffer.duration * 24000), 24000);
  const source = offline.createBufferSource(); source.buffer = buffer; source.connect(offline.destination); source.start();
  const samples = (await offline.startRendering()).getChannelData(0);
  const out = new ArrayBuffer(44 + samples.length * 2), view = new DataView(out);
  const text = (offset,s) => [...s].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
  text(0,'RIFF'); view.setUint32(4,36+samples.length*2,true); text(8,'WAVE'); text(12,'fmt ');
  view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
  view.setUint32(24,24000,true); view.setUint32(28,48000,true); view.setUint16(32,2,true); view.setUint16(34,16,true);
  text(36,'data'); view.setUint32(40,samples.length*2,true);
  samples.forEach((s,i)=>view.setInt16(44+i*2,Math.round(Math.max(-1,Math.min(1,s))*(s<0?32768:32767)),true));
  return new Blob([out],{type:'audio/wav'});
}
