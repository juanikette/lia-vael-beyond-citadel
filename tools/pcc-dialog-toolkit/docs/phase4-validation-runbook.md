# Fase 4 - Validacion real TLK (ME2 OT)

Comando reproducible para validar resolucion de `StrRef` con TLK base y DLC:

```bash
PYTHONPATH=src python -c "from pathlib import Path; import json; from pcc import read_pcc; from dialogue import parse_all_bioconversation_stubs; from tlk import build_tlk_resolver, resolve_conversations_tlk; game=Path(r'C:\\Program Files\\EA Games\\Mass Effect 2'); cooked=game/'BioGame'/'CookedPC'; tlk= cooked/'BIOGame_INT.tlk'; dlc=game/'BioGame'/'DLC'; pccs=sorted(cooked.glob('BioD_*LOC_INT.pcc')); base=build_tlk_resolver(base_tlk_path=tlk, dlc_dir=None); with_dlc=build_tlk_resolver(base_tlk_path=tlk, dlc_dir=dlc); files=0; conv=0; entry_refs=0; entry_res_base=0; entry_res_dlc=0; reply_refs=0; reply_res_base=0; reply_res_dlc=0; diff=0; parse_errors=[]; \
for p in pccs:\
  try:\
    pkg=read_pcc(p); stubs=parse_all_bioconversation_stubs(pkg); rb=resolve_conversations_tlk(stubs, base); rd=resolve_conversations_tlk(stubs, with_dlc); files+=1; conv+=len(stubs)\
    for cb,cd in zip(rb,rd):\
      for eb,ed in zip(cb.entries, cd.entries):\
        if eb.line_strref is not None and eb.line_strref>=0:\
          entry_refs+=1; entry_res_base += 1 if eb.line_text is not None else 0; entry_res_dlc += 1 if ed.line_text is not None else 0; diff += 1 if eb.line_text != ed.line_text else 0\
      for rb1,rd1 in zip(cb.replies, cd.replies):\
        if rb1.line_strref is not None and rb1.line_strref>=0:\
          reply_refs+=1; reply_res_base += 1 if rb1.line_text is not None else 0; reply_res_dlc += 1 if rd1.line_text is not None else 0; diff += 1 if rb1.line_text != rd1.line_text else 0\
  except Exception as exc:\
    parse_errors.append({'file':str(p.name),'error':str(exc)})\
out={'scope':{'files_considered':len(pccs),'files_processed':files,'tlk_base':str(tlk),'dlc_dir':str(dlc)},'totals':{'conversations':conv,'entry_strrefs':entry_refs,'entry_resolved_base':entry_res_base,'entry_resolved_with_dlc':entry_res_dlc,'reply_strrefs':reply_refs,'reply_resolved_base':reply_res_base,'reply_resolved_with_dlc':reply_res_dlc,'text_differences_base_vs_dlc':diff},'parse_errors_count':len(parse_errors),'parse_errors_sample':parse_errors[:5]}; print(json.dumps(out, ensure_ascii=False))"
```

Notas:

- Requiere `lzallright` para PCC ME2 OT comprimidos.
- El resolver DLC ignora `*_Test_INT.tlk` por defecto.
- Si `Mount.dlc` no existe en una carpeta DLC, el orden usa fallback estable por ruta.
