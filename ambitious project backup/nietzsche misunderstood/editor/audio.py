import subprocess

def audio_pauses(c):
    return c['audio'].get('pauses', [])

def prepare_audio(c, base, output):
    """Keep narration timing, soften board endings, and fill pulls with wing SFX."""
    rate = 48000
    pauses = audio_pauses(c)
    total = round(c['audio'].get('source_duration', c['duration']) * rate)
    cuts = [0] + [round(p['source_time'] * rate) for p in pauses] + [total]
    count = len(cuts) - 1
    fade_out = c['audio'].get('transition_fade_out', 0.0)
    fade_in = c['audio'].get('transition_fade_in', 0.0)
    sfx = c['audio'].get('transition_sfx', {})
    use_sfx = bool(sfx.get('path') and pauses)
    graph = [f'[0:a]aresample={rate},aformat=sample_fmts=s16:channel_layouts=stereo,'
             f'apad,atrim=end_sample={total},asplit={count}' +
             ''.join(f'[source{i}]' for i in range(count))]
    if use_sfx:
        graph.append(f'[1:a]aresample={rate},aformat=channel_layouts=stereo,'
                     f'asplit={len(pauses)}' + ''.join(f'[flap{i}]' for i in range(len(pauses))))
    parts = []
    for i, (start, end) in enumerate(zip(cuts, cuts[1:])):
        length = (end-start)/rate
        filters = [f'atrim=start_sample={start}:end_sample={end}', 'asetpts=PTS-STARTPTS']
        if fade_in > 0 and i > 0:
            filters.append(f'afade=t=in:st=0:d={min(fade_in,length/2):.6f}:curve=qsin')
        if fade_out > 0:
            fade = min(fade_out, length/2)
            filters.append(f'afade=t=out:st={length-fade:.6f}:d={fade:.6f}:curve=qsin')
        graph.append(f'[source{i}]' + ','.join(filters) + f'[voice{i}]')
        parts.append(f'[voice{i}]')
        if i < len(pauses):
            samples = round(pauses[i]['duration'] * rate)
            if use_sfx:
                offset = round(sfx.get('source_start', 0)*rate)
                length = samples/rate
                fade_in_sfx = min(sfx.get('fade_in', .08), length/2)
                fade_out_sfx = min(sfx.get('fade_out', .18), length/2)
                graph.append(f'[flap{i}]atrim=start_sample={offset}:end_sample={offset+samples},'
                             f'asetpts=PTS-STARTPTS,apad,atrim=end_sample={samples},'
                             'highpass=f=60,acompressor=threshold=0.08:ratio=4:attack=5:release=80:makeup=2,'
                             f'volume={sfx.get("volume", .8)},'
                             'alimiter=limit=0.35:level=false:latency=true,'
                             f'afade=t=in:st=0:d={fade_in_sfx}:curve=qsin,'
                             f'afade=t=out:st={length-fade_out_sfx}:d={fade_out_sfx}:curve=qsin[pull{i}]')
            else:
                graph.append(f'anullsrc=r={rate}:cl=stereo,atrim=end_sample={samples},'
                             f'asetpts=PTS-STARTPTS[pull{i}]')
            parts.append(f'[pull{i}]')
    graph.append(''.join(parts) + f'concat=n={len(parts)}:v=0:a=1[out]')
    inputs = ['-i', str(base / c['audio']['path'])]
    if use_sfx:
        inputs += ['-i', str(base / sfx['path'])]
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    *inputs, '-filter_complex', ';'.join(graph),
                    '-map', '[out]', '-c:a', 'pcm_s16le', str(output)], check=True)
