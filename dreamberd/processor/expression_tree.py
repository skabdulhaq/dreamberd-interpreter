from __future__ import annotations
from abc import ABCMeta, abstractmethod

from dreamberd.base import STR_TO_OPERATOR, Token, TokenType, OperatorType, InterpretationError, VAR_DECL_KW, raise_error_at_token

class ExpressionTreeNode(metaclass=ABCMeta):
    @abstractmethod
    def to_string(self, tabs: int = 0) -> str: pass

class ListNode(ExpressionTreeNode):
    def __init__(self, values: list[ExpressionTreeNode]):
        self.values = values
    def to_string(self, tabs: int = 0) -> str:
        return f"{'  ' * tabs}List: \n" + \
               f"{'  ' * (tabs + 1)}Values: \n" + \
               "\n".join([f"{v.to_string(tabs + 2)}" for v in self.values])

class ExpressionNode(ExpressionTreeNode):
    def __init__(self, left: ExpressionTreeNode, right: ExpressionTreeNode, operator: OperatorType):
        self.left = left 
        self.right = right
        self.operator = operator
    def to_string(self, tabs: int = 0) -> str:
        return f"{'  ' * tabs}Expression: \n" + \
               f"{'  ' * (tabs + 1)}Operator: {self.operator}\n" + \
               f"{'  ' * (tabs + 1)}Left: \n" + \
               f"{self.left.to_string(tabs + 2)}\n" + \
               f"{'  ' * (tabs + 1)}Right: \n" + \
               f"{self.right.to_string(tabs + 2)}"

class FunctionNode(ExpressionTreeNode):
    def __init__(self, name: str, args: list[ExpressionTreeNode]):
        self.name = name 
        self.args = args
    def to_string(self, tabs: int = 0) -> str:
        return f"{'  ' * tabs}Function: \n" + \
               f"{'  ' * (tabs + 1)}Name: {self.name}\n" + \
               f"{'  ' * (tabs + 1)}Arguments: \n" + \
               "\n".join([f"{arg.to_string(tabs + 2)}" for arg in self.args]) 

class IndexNode(ExpressionTreeNode):
    def __init__(self, value: ExpressionTreeNode, index: ExpressionTreeNode):
        self.value = value 
        self.index = index
    def to_string(self, tabs: int = 0) -> str:
        return f"{'  ' * tabs}Index: \n" + \
               f"{'  ' * (tabs + 1)}Of: \n" + \
               f"{self.value.to_string(tabs + 2)}\n" + \
               f"{'  ' * (tabs + 1)}At: \n" + \
               f"{self.index.to_string(tabs + 2)}"

class Value(ExpressionTreeNode):
    def __init__(self, name_or_value: Token): 
        self.name_or_value = name_or_value
    def to_string(self, tabs: int = 0) -> str:
        return f"{'  ' * tabs}Value: {self.name_or_value}"

def build_expression_tree(filename: str, tokens: list[Token], code: str) -> ExpressionTreeNode:
    """ 
    This language has significant whitespace, so the biggest split happens where there is most space
     - func a, b  +  c becomes func(a, b) + c but func a, b+c  becomes func(a, b + c) 
     - a + func  b  ,  c + d is not legal because it translates to (a + func)(b, c + d)
     - 2 * 1+3 becomes 2 * (1 + 3)
    """

    if not tokens:
        raise InterpretationError("\033[31mSomething went wrong, I don't know what so figure it out :)\033[32m")

    for token in tokens:
        if token.type == TokenType.WHITESPACE and '\t' in token.value:
            raise_error_at_token(filename, code, "Tabs are not allowed in expressions.", token)
    
    # create a new list consisting and tokens and a brand new type: the list 
    tokens_without_whitespace = [token for token in tokens if token.type != TokenType.WHITESPACE]
    starts_with_whitespace = tokens[0].type == TokenType.WHITESPACE
    ends_with_whitespace = tokens[-1].type == TokenType.WHITESPACE

    # transform a list of tokens to include operators 
    # find the operator with the maximum whitespace between it and other things
    updated_list = [STR_TO_OPERATOR.get(token.value, token) for token in tokens]
    max_width, max_index = 0, -1
    bracket_layers = 0
    for i in range(len(updated_list)):
        if tokens[i].type == TokenType.L_SQUARE:
            bracket_layers += 1
        elif tokens[i].type == TokenType.R_SQUARE:
            bracket_layers -= 1
        if isinstance(updated_list[i], OperatorType) and bracket_layers == 0:
            try:
                l_len, r_len = 0, 0
                if tokens[i - 1].type == TokenType.WHITESPACE:
                    l_len = len(tokens[i - 1].value)
                if tokens[i + 1].type == TokenType.WHITESPACE:
                    r_len = len(tokens[i + 1].value)
                if l_len != r_len and updated_list[i] != OperatorType.COM:
                    raise_error_at_token(filename, code, "Whitespace must be equal on either side of an operator.", tokens[i])
                if r_len >= max_width:
                    max_width = r_len
                    max_index = i
            except IndexError:
                raise_error_at_token(filename, code, "Operator cannot be at the end of an expression.", tokens[i])

    # detecting single argument function
    # this doesn't seem to adhere to my standards 100%, so its not a bug, its a feature
    first_name_index = int(starts_with_whitespace)
    if len(tokens) >= 3 + first_name_index and \
       tokens[first_name_index].type == TokenType.NAME and \
       tokens[first_name_index + 1].type == TokenType.WHITESPACE and \
       tokens[first_name_index + 2].type in [TokenType.NAME, TokenType.L_SQUARE, TokenType.STRING] and \
       len(tokens[first_name_index + 1].value) > max_width:
        return FunctionNode(tokens[first_name_index].value,
                            [build_expression_tree(filename, tokens[first_name_index + 1:], code)])

    # there is no operator, must be just a value
    if max_index == -1:

        # just making sure the input is correct
        try:
            name_or_value = tokens_without_whitespace[0]
            if name_or_value.type not in [TokenType.NAME, TokenType.L_SQUARE, TokenType.STRING]:
                raise_error_at_token(filename, code, "Expected name or value.", tokens_without_whitespace[0])
        except IndexError:
            raise_error_at_token(filename, code, "Expected name or value.", tokens_without_whitespace[0])

        # this is a list :)
        if name_or_value.type == TokenType.L_SQUARE:
            bracket_layers = 1
            for i, token in enumerate(tokens_without_whitespace[1:], start=1):
                if token.type == TokenType.L_SQUARE:
                    bracket_layers += 1 
                elif token.type == TokenType.R_SQUARE:
                    bracket_layers -= 1

                # this means the closing happen, signifying the end of the list
                if bracket_layers == 0:
                    if i == len(tokens_without_whitespace) - 1:
    
                        # let's find the most significant comma, and split by that
                        # if there's a function in the middle of the list, too bad :)
                        # [func a, b]  == [func(a), b] and also [func(a, b)]  # literally how do i tell them apart

                        # literally need to consider the width of whitespace from either side fr
                        l_width = len(token.value) if (token := tokens[int(starts_with_whitespace) + 1]).type == TokenType.WHITESPACE else 0
                        r_width = len(token.value) if (token := tokens[len(tokens) - int(ends_with_whitespace) - 2]).type == TokenType.WHITESPACE else 0
                        if l_width != r_width:
                            raise_error_at_token(filename, code, "Whitespace between either bracket of a list must be equal in length.",
                                                 tokens[len(tokens) - int(ends_with_whitespace) - 2])

                        # now go through all the commas and check if the whitespace is significant
                        all_commas = []
                        bracket_layers = 0  # yes i'm setting this damn thing twice 
                        for i, (token, tok_or_op) in enumerate(zip(tokens[:-1], updated_list)):  # stop here to avoid angry errors
                            if token.type == TokenType.L_SQUARE:
                                bracket_layers += 1 
                            elif token.type == TokenType.R_SQUARE:
                                bracket_layers -= 1
                            if tok_or_op == OperatorType.COM and bracket_layers == 1 and (
                                l_width == 0 or l_width == len(tokens[i + 1].value) and tokens[i + 1].type == TokenType.WHITESPACE
                            ):
                                all_commas.append(i)

                        # not single element
                        if all_commas:
                            return ListNode([
                                build_expression_tree(filename, t, code) for t in [
                                    tokens[comma_index + 1:next_index] for comma_index, next_index in 
                                    zip([int(starts_with_whitespace), *all_commas], 
                                        [*all_commas, len(tokens) - 1 - int(ends_with_whitespace)])  # adjusting here in order to avoid the bracket tokens
                                ]
                            ])
                        
                        # single element :)
                        return ListNode([build_expression_tree(filename, tokens[int(starts_with_whitespace) + 1 : len(tokens) - int(ends_with_whitespace) - 1], code)])
                    break

        # now we need to handle indexes
        # let's go from the back of the list and find the first fully closing sequence 
        # i am sure that this guarantees there is an index (i think)
        if tokens_without_whitespace[-1].type == TokenType.R_SQUARE:
            bracket_layers = -1
            end_index = len(tokens) - int(ends_with_whitespace) - 1
            for i, token in reversed(list(enumerate(tokens[:end_index]))):  # i don't like this one bit  :(
                if token.type == TokenType.L_SQUARE:
                    bracket_layers += 1 
                elif token.type == TokenType.R_SQUARE:
                    bracket_layers -= 1

                # first index!!!!!!!!!!!!!!!!!!!!
                if bracket_layers == 0:
                    return IndexNode(build_expression_tree(filename, tokens[int(starts_with_whitespace) : i], code),
                                     build_expression_tree(filename, tokens[i + 1 : end_index], code))
                    
        return Value(name_or_value)
        
    # max_index is the token with the maximum surrouding whitespace 
    if updated_list[max_index].value == ',':  
        # this means it is a function
        # we need to find every other comma as they become the arguments of the function
        # additionally, there needs to be a spacing of equal length between the name of the function and the next argument
        
        if tokens_without_whitespace[0].type != TokenType.NAME or \
           tokens_without_whitespace[1].type not in [TokenType.NAME, TokenType.L_SQUARE, TokenType.STRING]:
            raise_error_at_token(filename, code, "Expected function call. This is likely an issue of whitespace, as DreamBerd replaces parentheses with spaces and has significant whitespace.", tokens_without_whitespace[0])
        
        all_commas = []
        for i in range(len(updated_list)):
            if updated_list[i].value == ',':  # okay this is weird because enums have .value and tokens have .value
                if max_width == 0 or (tokens[i + 1].type == TokenType.WHITESPACE and len(tokens[i + 1].value)) == max_width:
                    all_commas.append(i)
        
        # i have no idea what the hell im doin
        return FunctionNode(tokens_without_whitespace[0].value, [
            build_expression_tree(filename, t, code) for t in [
                tokens[comma_index + 1:next_index] for comma_index, next_index in 
                zip([int(starts_with_whitespace), *all_commas], [*all_commas, len(tokens)])
            ]
        ])

    else: 
        return ExpressionNode(
            build_expression_tree(filename, tokens[:max_index], code), 
            build_expression_tree(filename, tokens[max_index + 1:], code), 
            operator=updated_list[max_index]
        )
