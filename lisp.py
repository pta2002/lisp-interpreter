L_nil = None

class LispType(object):
    def get_val(self, env, vars={}):
        return L_nil

class Lisp_Int(LispType):
    def __init__(self, num):
        self.val = num
    def get_val(self, env, vars={}):
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
    def __int__(self):
        return self.val

class Lisp_Bool(LispType):
    def __init__(self, val):
        self.val = val
    def get_val(self, env, vars={}):
        return self.val
    def __bool__(self):
        return self.val
    def __int__(self):
        return 1 if self.val else 0

class Lisp_String(LispType):
    def __init__(self, s):
        self.val = s
    def get_val(self, env, vars={}):
        return self.val
    def __str__(self):
        return self.val

class Lisp_List(LispType):
    def __init__(self, items):
        self.val = items
    def get_val(self, env, vars={}):
        return self.val

class Lisp_Keyword(LispType):
    def __init__(self, kw):
        self.keyword = kw
    def get_val(self, env, vars={}):
        return self.keyword

class Lisp_Block(LispType):
    def __init__(self, body):
        self.body = body
    def get_val(self, env, vars={}):
        return env.run_ast(self, vars=vars)
    def __str__(self):
        return str(self.body)

class Lisp_Var(LispType):
    def __init__(self, var):
        self.var = var
    def get_val(self, env, vars={}):
        v = {**env.vars, **vars}
        return v[self.var]

class Lisp_Function(LispType):
    def __init__(self, params, body):
        self.body = body
        self.params = params
    def get_val(self, env, vars={}):
        return self
    def run(self, args, env, vars={}):
        params = {}
        if len(args) != len(self.params):
            raise Exception("Function %s expects %d arguments, %d given." % (self.name, len(self.params), len(args)))
        for arg in range(len(args)):
            params[self.params[arg]] = args[arg]

        return env.run_ast(self.body, vars={**vars, **params})



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
                    if ins[0].strip() not in '0123456789"()':
                        ast.append(Lisp_Keyword(ins))
                else:
                    if ins[0] == "\"":
                        ast.append(Lisp_String(ins[1:-1]))
                    elif ins[0] in '0123456789':
                        try:
                            ast.append(Lisp_Int(int(ins)))
                        except ValueError:
                            raise Exception("Not a number: %s" % ins)
                    elif ins == 'true':
                        ast.append(Lisp_Bool(True))
                    elif ins == 'false':
                        ast.append(Lisp_Bool(False))
                    elif ins.strip() != '':
                        ast.append(Lisp_Var(ins))

        return Lisp_Block(ast)

    def run(self):
        self.run_ast(self.ast)

    def run_ast(self, ast, vars={}):
        vars = {**self.vars, **vars}
        if type(ast.body[0]) == Lisp_Keyword:
            if ast.body[0].keyword == 'if':
                if len(ast.body) < 3:
                    raise Exception("if expected at least 2 parameters")
                if ast.body[1].get_val(self, vars=vars):
                    self.run_ast(ast.body[2],vars=vars)
                elif len(ast.body) == 4:
                    self.run_ast(ast.body[3],vars=vars)
                return L_nil
            elif ast.body[0].keyword == 'while':
                if len(ast.body) != 3:
                    raise Exception("while expects 2 parameters")
                while ast.body[1].get_val(self, vars=vars):
                    self.run_ast(ast.body[2], vars=vars)
                return L_nil
            elif ast.body[0].keyword == 'set':
                self.vars[ast.body[1].var] = ast.body[2].get_val(self, vars=vars)
                return L_nil
            elif ast.body[0].keyword == 'defun':
                params = []
                for x in ast.body[2].body:
                    if type(x) == Lisp_Var:
                        params.append(x.var)
                    elif type(x) == Lisp_Keyword:
                        params.append(x.keyword)
                self.funcs[ast.body[1].var] = Lisp_Function(params, ast.body[3])
                return L_nil

        to_run = None
        args = []
        for i in ast.body:
            if type(i) == Lisp_Block:
                args.append(self.run_ast(i, vars=vars))
            elif type(i) == Lisp_Keyword:
                to_run = i.keyword
            elif type(i) == Lisp_Var:
                args.append(vars.get(i.var, L_nil))
            else:
                args.append(i)

        if to_run:
            if to_run in self.funcs:
                return self.funcs[to_run].run(args, self, vars)
            else:
                if to_run == 'add':
                    return sum(args)
                elif to_run == 'sub':
                    s = args[0]
                    for i in args[1:]:
                        s -= i
                    return s
                elif to_run == 'write-line':
                    print(*[x.get_val(self, vars=vars) if isinstance(x, LispType) else x for x in args])
                elif to_run == ">":
                    return args[0] > args[1]
                elif to_run == "<":
                    return int(args[0]) < int(args[1])
                else:
                    raise Exception("%s not found" % i)
                
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
                making = braces[i] + 1
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
