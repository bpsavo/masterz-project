from pyteal import *

def approval_program():
    on_creation = Seq([
        App.globalPut(Bytes("n_contributors"), Int(0)),
        App.globalPut(Bytes("amt_funded"), Int(0)),
        App.globalPut(Bytes("empty"), Int(0)),
        App.globalPut(Bytes("creator_address"), Txn.sender()),
        App.globalPut(Bytes("project_name"), Txn.application_args[0]),
        App.globalPut(Bytes("image"), Txn.application_args[1]),
        App.globalPut(Bytes("start_date"), Btoi(Txn.application_args[2])),
        App.globalPut(Bytes("end_date"), Btoi(Txn.application_args[3])),
        App.globalPut(Bytes("goal"), Btoi(Txn.application_args[4])),
        App.globalPut(Bytes("description"), Txn.application_args[5]),
        Approve()
    ])

    handle_optin = Seq([App.localPut(Txn.sender(),Bytes("amt_funded"), Int(0)),
                        Approve()])

    handle_closeout = Reject()

    handle_updateapp = Reject()

    handle_deleteapp = Reject()

    scratch = ScratchVar(TealType.uint64)
    scratch_l = ScratchVar(TealType.uint64)
    scratch_n = ScratchVar(TealType.uint64)

    retrieve =  Seq(
                    [Assert(
                        And(Txn.sender() == App.globalGet(Bytes("creator_address")),
                            Global.latest_timestamp() > App.globalGet(Bytes("end_date")),
                            App.globalGet(Bytes("empty")) == Int(0),
                            App.globalGet(Bytes("amt_funded")) > (Int(1000) + Int(100000))
                        )
                    ),
                    scratch.store(App.globalGet(Bytes("amt_funded")) - Int(1000) - Int(100000)),
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetFields({
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: scratch.load(),
                        TxnField.receiver: App.globalGet(Bytes("creator_address")),
                    }),
                    InnerTxnBuilder.Submit(),
                    App.globalPut(Bytes("empty"), Int(1)),
                    Approve()
                    ])

    fund =  Seq([
                Assert(
                    And(Gtxn[1].application_args.length() == Int(2),                                   
                        Gtxn[0].sender() != App.globalGet(Bytes("creator_address")), 
                        Global.latest_timestamp() > App.globalGet(Bytes("start_date")),
                        Global.latest_timestamp() < App.globalGet(Bytes("end_date")),       
                        Gtxn[0].amount() == Btoi(Gtxn[1].application_args[1]),                   
                        Gtxn[0].receiver() == Global.current_application_address(),        
                        App.globalGet(Bytes("empty")) == Int(0)
                    )
                ),                          
                scratch.store(App.globalGet(Bytes("amt_funded"))),
                scratch_l.store(App.localGet(Gtxn[0].sender(), Bytes("amt_funded"))),
                scratch_n.store(App.globalGet(Bytes("n_contributors"))),
                App.globalPut(Bytes("amt_funded"), (scratch.load() + Gtxn[0].amount())),
                App.localPut(Gtxn[0].sender(), Bytes("amt_funded"), scratch_l.load() + Gtxn[0].amount()),
                App.globalPut(Bytes("n_contributors"), scratch_n.load() + Int(1)),
                Approve()
                ])

    handle_noop = Cond(
        [And(
            Global.group_size() == Int(2),
            Txn.application_args[0] == Bytes("Fund")
        ), fund],
        [And(
            Global.group_size() == Int(1),
            Txn.application_args[0] == Bytes("Retrieve funds")
        ), retrieve],
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop]
    )
    # Mode.Application specifies that this is a smart contract
    return compileTeal(program, Mode.Application, version=5)

def clear_state_program():
    program = Approve()
    # Mode.Application specifies that this is a smart contract
    return compileTeal(program, Mode.Application, version=5)


def main():
    # compile program to TEAL assembly
    with open("./cfunding_approval.teal", "w") as f:
        approval_program_teal = approval_program()
        f.write(approval_program_teal)
        print("Compiled approval program!")


    # compile program to TEAL assembly
    with open("./cfunding_clear.teal", "w") as f:
        clear_state_program_teal = clear_state_program()
        f.write(clear_state_program_teal)
        print("Compiled clear state!")


main()