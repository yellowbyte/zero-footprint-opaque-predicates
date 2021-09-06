(* Based off of: https://stackoverflow.com/questions/36132777/frama-c-plugin-development-getting-result-of-value-analysis *)

open Cil_types


(* Return true if [s2] is a substring of [s1]. Else, return false *)
let contains s1 s2 =
    let re = Str.regexp_string s2
    in
      try ignore (Str.search_forward re s1 0); true
      with Not_found -> false


(* Prints the value associated to a pointer *)
let pretty_lval fmt stmt lval vi =
  let kinstr = Kstmt stmt in (* Make a kinstr from a stmt *)
  let loc = (* Make a location from a kinstr + an lval *)
    !Db.Value.lval_to_loc kinstr ~with_alarms:CilE.warn_none_mode lval
  in
  match vi.vtype with
  | TInt (ikind,_) -> begin
      match ikind with 
      | IUInt | IUShort | IUChar | IULong | IULongLong -> 
        (* Ignore unsigned variable since it messes with the opaque predicate tool  *)
        ()
      | _ -> begin
        Db.Value.fold_state_callstack
          (fun state () ->
             (* For each state in the callstack *)
             let value = Db.Value.find state loc in (* obtain value for location *)
             (* Print variable name and corresponding value set *)
             Format.fprintf fmt "\"%a:%a\",@." Printer.pp_lval lval
               Locations.Location_Bytes.pretty value (* print mapping *)
          ) () ~after:true kinstr; (* Get value set after execution of statement  *)
        end
    end
  | _ -> begin
    Db.Value.fold_state_callstack
      (fun state () ->
         (* For each state in the callstack *)
         let value = Db.Value.find state loc in (* obtain value for location *)
         (* Print variable name and corresponding value set *)
         Format.fprintf fmt "\"%a:%a\",@." Printer.pp_lval lval
           Locations.Location_Bytes.pretty value (* print mapping *)
      ) () ~after:true kinstr; (* Get value set after execution of statement  *)
    end


(* Prints the value associated to variable [vi] before [stmt]. *)
let pretty_vi fmt stmt vi =
  let kinstr = Kstmt stmt in (* Make a kinstr from a stmt *)
  let lval = (Var vi, NoOffset) in (* Make an lval from a varinfo *)
  let loc = (* Make a location from a kinstr + an lval *)
    !Db.Value.lval_to_loc kinstr ~with_alarms:CilE.warn_none_mode lval
  in
  match vi.vtype with
  | TInt (ikind,_) -> begin
      match ikind with 
      | IUInt | IUShort | IUChar | IULong | IULongLong -> 
        (* Ignore unsigned variable since it messes with the opaque predicate tool  *)
        ()
      | _ -> begin
        Db.Value.fold_state_callstack
          (fun state () ->
             (* For each state in the callstack *)
             let value = Db.Value.find state loc in (* obtain value for location *)
             (* Print variable name and corresponding value set *)
             Format.fprintf fmt "\"%a:%a\",@." Printer.pp_varinfo vi
               Locations.Location_Bytes.pretty value (* print mapping *)
          ) () ~after:true kinstr; (* Get value set after execution of statement  *)
        end
    end
  | _ -> begin
    Db.Value.fold_state_callstack
      (fun state () ->
         (* For each state in the callstack *)
         let value = Db.Value.find state loc in (* obtain value for location *)
         (* Print variable name and corresponding value set *)
         Format.fprintf fmt "\"%a:%a\",@." Printer.pp_varinfo vi
           Locations.Location_Bytes.pretty value (* print mapping *)
      ) () ~after:true kinstr; (* Get value set after execution of statement  *)
    end


(* Prints the state at statement [stmt] for each local variable in [kf],
   and for each global variable. *)
let pretty_local_and_global_vars kf fmt stmt =
  (* Handles local variables *)
  let locals = Kernel_function.get_locals kf in
  print_endline "END_OF_METADATA"; 
  print_endline "["; 
  List.iter (fun vi -> 
    if Cil.isPointerType vi.vtype then
      (* Variable is a pointer. Print it as such so user knows *)
      let lval = (Mem (Cil.evar vi), NoOffset) in
      pretty_lval fmt stmt lval vi
    else if Cil.isArrayType vi.vtype then
      (* Defined array. Skip *)
      ()
    else 
      (* Normal variable *)
      pretty_vi fmt stmt vi) locals;

  (* Handles global variables *)
  Globals.Vars.iter (fun vi ii -> 
    let s = Format.asprintf "%a" Printer.pp_location vi.vdecl in 
    if (contains s "root/.opam/default/") == false && (contains s "FRAMAC_SHARE") == false then
      (* Filter out internal Frama-C variables, which has paths that start with root/.opam/default/ or :0 *)
      if Cil.isPointerType vi.vtype then
        (* Variable is a pointer. Print it as such so user knows *)
        let lval = (Mem (Cil.evar vi), NoOffset) in
        pretty_lval fmt stmt lval vi
      else if Cil.isArrayType vi.vtype then
        (* Defined array. Skip *)
        ()
      else 
        (* Normal variable *)
        pretty_vi fmt stmt vi         
  );
  print_endline "]"; 
  print_string "----------"; 


(* Visits each statement in function [kf] and prints the result of Value before the statement. *)
(* kf represents a function *)
class stmt_val_visitor kf =
  object (self)
    inherit Visitor.frama_c_inplace
    method! vstmt_aux stmt =
      (match stmt.skind with
       | Instr _ ->
         Format.printf "current instruction: %a@."
           Printer.pp_stmt stmt; (* Code at current line  *)
         (* Format: filename and line number, variable name, value-sets *)
         Format.printf "current line: %a@.%a@." 
           Printer.pp_location (Cil_datatype.Stmt.loc stmt) 
           (* Printer.pp_stmt stmt *) (* Code at current line  *)
           (* Function call to the rest of the code to get value sets *)
           (pretty_local_and_global_vars kf) stmt;
       | _ -> ());
      Cil.DoChildren
  end


(* Start *)
(* EX: frama-c -eva -eva-slevel 100 -eva-warn-key alarm=inactive -eva-auto-loop-unroll 300 -load-script /prettyvsa.ml 2048.c *)
let () =
  Db.Main.extend (fun () ->
      Format.printf "START PRETTY VSA @.";
      !Db.Value.compute ();
      Globals.Functions.iter
        (fun kf ->
          let s = Format.asprintf "%a" Printer.pp_location (Kernel_function.get_location kf) in 
          if (contains s "root/.opam/default/") == false && (contains s "FRAMAC_SHARE") == false then
            (* Filter functions that are not present in original source code *)
            let kf_vis = new stmt_val_visitor in
            let fundec = Kernel_function.get_definition kf in
            (* Kernel.log "kf = %s\n" (Kernel_function.get_name kf); *) (* current function *)
            ignore (Visitor.visitFramacFunction (kf_vis kf) fundec);
        ))
