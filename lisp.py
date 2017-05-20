L_nil = None

class LispType(object):
    def get_val(self, env):
        return L_nil

class Lisp_Int(LispType):
    def __init__(self, num):
        self.val = num
    def get_val(self, env):
        return self.val
    def __add__(self, o):
        return self.val + o
    def __sub__(self, o):
        return self.val - o
    def __rsub__(self, o):
        return o - self.val
    def __radd__(self, o):
        return o + self.val
    def __mul__(self, o):
        return self.val * o
    def __lt__(self, o):
        return self.val < o
    def __gt__(self, o):
        return self.val > o

class Lisp_String(LispType):
    def __init__(self, s):
        self.val = s
    def get_val(self, env):
        return self.val
    def __str__(self):
        return self.val

class Lisp_List(LispType):
    def __init__(self, items):
        self.val = items
    def get_val(self, env):
        return self.val

class Lisp_Keyword(LispType):
    def __init__(self, kw):
        self.keyword = kw
    def get_val(self, env):
        return self.keyword

class Lisp_Block(LispType):
    def __init__(self, body):
        self.body = body
    def get_val(self, env):
        return env.run_ast(self)
    def __str__(self):
        return str(self.body)

class Lisp_Var(LispType):
    def __init__(self, var):
        self.var = var
    def get_val(self, env):
        return env.variables[self.var]

class Lisp_Function(LispType):
    def __init__(self, name, params):
        self.name = name
        self.params = params
    def get_val(self, env):
        return self
    def run(self, args, env):
        params = {}
        if len(args) != len(self.params):
            raise Exception("Function %s expects %d arguments, %d given." % (self.name, len(self.params), len(args)))
        for arg in range(len(args)):
            params[self.params[arg]] = args[arg]

        return env.run(self.body, extra=params)



class Lisp_Environment(object):
    def __init__(self, code):
        self.code = code
        self.ast = self.parse(code)
        self.vars = {}
        self.funcs = {}

    def parse(self, code):
        ast = []
        braces = match_braces(code)

        inst = []
        
        i = 0

        while i < len(code):
            if i in braces:
                inst.append(self.split_lisp(code[i:braces[i]+1]))
                i = braces[i]
            i += 1
        
        return self.make_ast(inst)

    def make_ast(self, instructions):
        ast = []

        for i, ins in enumerate(instructions):
            if type(ins) == list:
                ast.append(self.make_ast(ins))
            else:
                if i == 0:
                    if ins[0] not in '0123456789"()':
                        ast.append(Lisp_Keyword(ins))
                else:
                    if ins[0] == "\"":
                        ast.append(Lisp_String(ins[1:-1]))
                    elif ins[0] in '0123456789':
                        try:
                            ast.append(Lisp_Int(int(ins)))
                        except ValueError:
                            raise Exception("Not a number: %s" % ins)
                    else:
                        ast.append(Lisp_Var(ins))

        return Lisp_Block(ast)

    def run(self):
        self.run_ast(self.ast)

    def run_ast(self, ast):
        if type(ast.body[0]) == Lisp_Keyword:
            if ast.body[0].keyword == 'if':
                if len(ast.body) < 3:
                    raise Exception("if expected at least 2 parameters")
                if self.run_ast(ast.body[1]):
                    self.run_ast(ast.body[2])
                elif len(ast.body) == 4:
                    self.run_ast(ast.body[3])
                return L_nil
            elif ast.body[0].keyword == 'set':
                self.vars[ast.body[1].var] = ast.body[2].get_val(self)
                return L_nil

        to_run = None
        args = []
        for i in ast.body:
            if type(i) == Lisp_Block:
                args.append(self.run_ast(i))
            elif type(i) == Lisp_Keyword:
                to_run = i.keyword
            elif type(i) == Lisp_Var:
                args.append(self.vars[i.var])
            else:
                args.append(i)

        if to_run:
            if to_run in self.funcs:
                return self.funcs[i.keyword].run(args)
            else:
                if to_run == 'add':
                    return sum(args)
                elif to_run == 'sub':
                    s = args[0]
                    for i in args[1:]:
                        s -= i
                    return s
                elif to_run == 'write-line':
                    print(*[x.get_val(self) if isinstance(x, LispType) else x for x in args])
                elif to_run == ">":
                    return args[0] > args[1]
                elif to_run == "<":
                    return args[0] < args[1]
                elif to_run == "set":
                    self.vars[args[0]] = args[1]
                    return T_nil
                else:
                    raise Exception("%s not found" % i.keyword)
                
    def split_lisp(self, code):
        m = []
        making = 0
        code = code[1:-1]
        braces = match_braces(code)
        quotes = match_quotes(code)
        i = 0
        while i < len(code):
            if code[i] == "(":
                m.append(self.split_lisp(code[i:braces[i]+1]))
                making = braces[i]
                i = braces[i]
            elif code[i] == "\"" and (i == 0 or code[i-1] != "\\"):
                m.append(code[i:quotes[i]+1])
                making = quotes[i]
                i = quotes[i]
            elif code[i] == " " or code[i] == "\t" or code[i] == "\n":
                if code[making:i] != "":
                    m.append(code[making:i])
                    making = i + 1
            elif i == len(code) - 1:
                m.append(code[making:i+1])
            i += 1
        return m

def match_braces(code):
    stack = []
    braces = {}

    for i, c in enumerate(code):
        if c == '(' and not is_string(code, i):
            stack.append(i)
        elif c == ')' and not is_string(code, i):
            braces[stack.pop()] = i
    return braces

def match_quotes(code):
    stack = []
    quotes = {}
    instr = False
    for i, c in enumerate(code):
        if c == "\"" and (i == 0 or code[i-1] != "\\"):
            if not instr:
                stack.append(i)
            else:
                quotes[stack.pop()] = i
            instr = not instr
    return quotes

def is_string(code, index):
    instr = False
    for i in range(index):
        if code[i] == "\"" and (i == 0 or code[i-1] != "\\"):
            instr = not instr
    return instr


if __name__ == '__main__':
    import sys
    with open(sys.argv[1], 'r') as f:
        code = f.read()
    env = Lisp_Environment(code)
    env.run()
