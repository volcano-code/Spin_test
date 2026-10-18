"""Strict binary/decimal rational regression for the native geometry adapter."""
from fractions import Fraction
import re
import pytest

def parse(token):
    parts=token.split('/')
    if len(parts)!=2:raise ValueError("not a rational pair")
    def integer(text,negative=False):
        sign=-1 if text.startswith('-') and negative else 1
        body=text[1:] if sign<0 else text
        base=2 if body.startswith('0b') else 10
        digits=body[2:] if base==2 else body
        if not digits or not re.fullmatch('[01]+' if base==2 else '[0-9]+',digits):
            raise ValueError("not canonical numeric digits")
        return sign*int(digits,base)
    numerator=integer(parts[0],True)
    denominator=integer(parts[1])
    if denominator<=0:raise ValueError("zero or signed denominator")
    return Fraction(numerator,denominator)

@pytest.mark.parametrize('binary,decimal',[
 ('0b0/0b1','0/1'),('0b101/0b10','5/2'),
 ('-0b101/0b110','-5/6'),('0b1/0b10000000000000000','1/65536')])
def test_producer_and_consumer_exact_same_rational(binary,decimal):
    assert parse(binary)==parse(decimal)

@pytest.mark.parametrize('bad',['0b/0b1','0b2/0b1','0b1/0b0',
 '-0b1/-0b1','0b1/0b11/0b1','0b1/0b', '0b1/','--1/1','1/+2'])
def test_invalid_rationals_rejected(bad):
    with pytest.raises(ValueError):parse(bad)
