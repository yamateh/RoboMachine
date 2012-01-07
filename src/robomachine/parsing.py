#  Copyright 2011-2012 Mikko Korpela
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from pyparsing import *
from robomachine.model import RoboMachine, State, Action, Variable
from robomachine.rules import AndRule, Condition, EquivalenceRule, OrRule


settings_table = Literal('*** Settings ***')+Regex(r'[^\*]+(?=\*)')
settings_table.setParseAction(lambda t: '\n'.join(t))
variables_table = Literal('*** Variables ***')+Regex(r'[^\*]+(?=\*)')
variables_table.setParseAction(lambda t: '\n'.join(t))
keywords_table = Literal('*** Keywords ***')+CharsNotIn('')+StringEnd()
keywords_table.setParseAction(lambda t: '\n'.join(t))

state_name = Regex(r'\w+( \w+)*')
state_name.leaveWhitespace()
state_name = state_name.setResultsName('state_name')

robo_step = Regex('([\w\$\{\}][ \w\$\{\}]*[\w\}]|\w)')
robo_step.leaveWhitespace()
robo_step = robo_step.setResultsName('robo_step')

variable = Regex(r'\$\{[_A-Z][_A-Z0-9]*\}')

variable_value = Regex(r'[\w\$\{\}!?]+( [\w\$\{\}!?]+)*')

variable_values = (variable_value+ZeroOrMore('  '+variable_value)).setResultsName('variable_values')
variable_values.setParseAction(lambda t: [[t[2*i] for i in range((len(t)+1)/2)]])

variable_definition = variable.setResultsName('variable_name') + '  any of  ' + variable_values + LineEnd()
variable_definition.leaveWhitespace()
variable_definition.setParseAction(lambda t: [Variable(t.variable_name, list(t.variable_values))])

condition_part = variable+' == '+variable_value
condition_part.setParseAction(lambda t: [Condition(t[0], t[2])])
condition_part.leaveWhitespace()

equivalence_rule = condition_part+'  <==>  '+condition_part
equivalence_rule.leaveWhitespace()
equivalence_rule.setParseAction(lambda t: [EquivalenceRule(t[0], t[2])])

and_rule = condition_part+ZeroOrMore('  and  '+condition_part)
and_rule.setParseAction(lambda t: [AndRule([t[i] for i in range(len(t)) if i % 2 == 0])])
and_rule.leaveWhitespace()

or_rule = condition_part+ZeroOrMore('  or  '+condition_part)
or_rule.setParseAction(lambda t: [OrRule([t[i] for i in range(len(t)) if i % 2 == 0])])
or_rule.leaveWhitespace()

rule = condition_part ^ equivalence_rule ^ and_rule ^ or_rule

step = Regex(r'  [^\n\[][^\n]*(?=\n)')+LineEnd()
step.leaveWhitespace()
step.setParseAction(lambda t: [t[0]])

action_header = White(min=2)+'[Actions]'

condition = Literal('  when  ')+rule
condition = condition ^ Regex(r'  +otherwise')
def parse_condition(cond):
    if cond[0] == '  when  ':
        return [cond[1]]
    return ['otherwise']

condition.leaveWhitespace()
condition.setParseAction(parse_condition)
condition = Optional(condition).setResultsName('condition')
action = White(min=4)+robo_step + White(min=2) + '==>'+White(min=2) + state_name + condition + LineEnd()
action.leaveWhitespace()
action.setParseAction(lambda t: [Action(t.robo_step.rstrip(), t.state_name, t.condition)])

actions = action_header + LineEnd() + OneOrMore(action).setResultsName('actions')
actions = Optional(actions)
actions.leaveWhitespace()
actions.setResultsName('actions')

comment = Regex(r'(^\s*\#[^\n]*\n)|(\s\s+\#[^\n]*(?=\n))')
comment.leaveWhitespace()

steps = ZeroOrMore(step).setResultsName('steps')

state = state_name + LineEnd() + steps + actions
state.leaveWhitespace()
state.setParseAction(lambda p: State(p.state_name, list(p.steps), list(p.actions)))

machine_header = Literal('*** Machine ***')+LineEnd()
states = state+ZeroOrMore(OneOrMore(LineEnd())+state)
states.setParseAction(lambda t: [[t[2*i] for i in range((len(t)+1)/2)]])
states = states.setResultsName('states')
variables = ZeroOrMore(variable_definition).setResultsName('variables')
rules = ZeroOrMore(rule+LineEnd()).setResultsName('rules')
rules.setParseAction(lambda t: [t[i] for i in range(len(t)) if i % 2 == 0])
machine = Optional(settings_table).setResultsName('settings_table')+\
          Optional(variables_table).setResultsName('variables_table')+\
          machine_header+ZeroOrMore(LineEnd())+variables+\
          ZeroOrMore(LineEnd())+rules+\
          ZeroOrMore(LineEnd())+states+\
          Optional(keywords_table).setResultsName('keywords_table')

def create_robomachine(p):
    return RoboMachine(list(p.states),
                       list(p.variables),
                       list(p.rules),
                       settings_table=p.settings_table,
                       variables_table=p.variables_table,
                       keywords_table=p.keywords_table)

machine.setParseAction(create_robomachine)
machine.ignore(comment)
machine.setWhitespaceChars(' ')

def parse(text):
    return machine.parseString(text, parseAll=True)[0]
