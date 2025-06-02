import sqlite3
import time
import os

class style:
    class component:
        def __init__(self, **kwargs) -> None:
            for var, value in kwargs.items():
                self.__setattr__(var, value)
    def __init__(self, fmt: str) -> None:
        self.sep = style.component(
            rows=fmt[0], col=fmt[1],
            up=fmt[2], down=fmt[3],
            left=fmt[4], right=fmt[5],
            fields=fmt[6], f_rows=fmt[7]
        )
        self.bor = style.component(ver=fmt[8], hor=fmt[9])
        self.cor = style.component(
            tl=fmt[10], tr=fmt[11],
            bl=fmt[12], br=fmt[13]
        )

formats = [
    style("─│┬┴├┤│┼│─┌┐└┘"),
    style("─│╤╧╟╢│┼║═╔╗╚╝"),
    style("═║╦╩╠╣║╬║═╔╗╚╝"),
]

def say(s, n=True, t=0.005):
    for w in s:
        print(w, end="", flush=True)
        time.sleep(t)
    if n: print()

def print_table(output, f, description):
    fields_max = [len(max(x, key=len)) for x in [[description[i]] + [str(output[j][i]) for j in range(len(output))] for i in range(len(description))]]
    say((f.cor.tl + f.sep.up.join(f.bor.hor*(fields_max[index]+2) for index in range(len(description))) + f.cor.tr), t=0.001) # type: ignore
    say((f.bor.ver+ f.sep.fields.join(value.center(fields_max[index]+2) for index, value in enumerate(description)) + f.bor.ver), t=0.001) # type: ignore
    say((f.sep.left + f.sep.f_rows.join(f.sep.rows*(fields_max[index]+2) for index in range(len(description))) + f.sep.right), t=0.001) # type: ignore
    say(("\n".join((f.bor.ver + f.sep.col.join(str(value).center(fields_max[index]+2) for index, value in enumerate(row)) + f.bor.ver) for row in output)), t=0.001) # type: ignore
    say((f.cor.bl + f.sep.down.join(f.bor.hor*(fields_max[index]+2) for index in range(len(description))) + f.cor.br), t=0.001) # type: ignore

def test_shell():
    say("Enter File Path: ", n = False)
    con = sqlite3.connect(input(), check_same_thread=False)
    cur = con.cursor()
    
    say("Enter table format index: ", False)
    f = formats[int(input())]
    print()

    while True:
        say("ghost DB :> ", n = False)
        cmd = input()
        if cmd == "exit":
            say("Have a nice day ...")
            exit()
        elif cmd == "cls":
            os.system("cls")
            continue
        cur.execute(cmd)
        data = cur.fetchall()
        if data: print_table(data, f, [x[0] for x in cur.description])
        print()

say(
    "Choose:\n"
    "   1. Production\n"
    "   2. Testing\n"
    "   3. Again\n"
    "   4. Exit\n"
    " :(enter option no.):> ",
    n = False
)

c = int(input())

while c <= 4:
    if c == 1:
        say("Yeah ...... ok ...... loading ...... byee ...............")
        exit()
    elif c == 2:
        test_shell()
        exit()
    elif c == 3: pass
    elif c == 4:
        say("Have a nice day ...")
        exit()
    else: pass
    say(" :(enter option no.):> ", n = False)
    c = int(input())