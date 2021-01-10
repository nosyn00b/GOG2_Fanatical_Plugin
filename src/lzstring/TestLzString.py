"""
Copyright © 2021 nosyn00b <nosyn00b71@gmail.com>
This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See the COPYING file for more details.

"""

import json
import lzstring
import base64

if __name__ == '__main__':
    x = lzstring.LZString()


    #s='(&$%_0?^é*+òù'#results in no padding when compressed
    #s='Ciao'#results in triple padding when compressed
    #s='Ciao!'#results in single padding when compressed
    #s='%_&Ciao//k!'#results in double padding when compressed
    s='Duke Nukem Forever,Duke Nukem Forever: The Doctor Who Cloned Me,Duke Nukem Forever: Hail to the Icons Parody Pack,Expeditions: Viking,The Surge'
 
    # generated with original LzString js lib
    #jsLzStringCompressToBase64 =               'BQMgJApA+gDA/APQJcCoDUAngn0A'#no padding 
    #jsLzStringCompressToBase64 =               'MISwhg9kA==='#triple padding
    #jsLzStringCompressToBase64 =               'MISwhg9ghEA='#singe padding
    #jsLzStringCompressToBase64 =               'KQfQZAwglghg9gegQawIRA=='#double padding
    jsLzStringCompressToBase64 =               'CIVw1gpgBAcuEFsoDED2AnCA3C6A0oks8SamO6AXFACoAW0wqAxgC4ZQDqdqUAwgBtUAOwgATKAFkIBeMUikM2XNQASAQwCWAqO10MoASWYiAzlAAK69KjEBPS+uZg8AUQAeAB3GbWms9QAappgmsIA5nj00ADKIOjhEEA=='


    #jsLzStringCompressToEncodedeUriComponent = 'BQMgJApA-gDA_APQJcCoDUAngn0A'#no padding
    #jsLzStringCompressToEncodedeUriComponent = 'MISwhg9kA'#triple padding
    #jsLzStringCompressToEncodedeUriComponent = 'MISwhg9ghEA'#single padding
    #jsLzStringCompressToEncodedeUriComponent = 'KQfQZAwglghg9gegQawIRA'#double padding
    jsLzStringCompressToEncodedeUriComponent = 'CIVw1gpgBAcuEFsoDED2AnCA3C6A0oks8SamO6AXFACoAW0wqAxgC4ZQDqdqUAwgBtUAOwgATKAFkIBeMUikM2XNQASAQwCWAqO10MoASWYiAzlAAK69KjEBPS-uZg8AUQAeAB3GbWms9QAappgmsIA5nj00ADKIOjhEEA'
    
    print('-------------------------------------')     
    print('ORIGINAL Uncompressed String:'+s)
    print('-------------------------------------')

    print('Compress WITH base64: TEST is OK if PHYTON-Side string is the same of the JS-Side one')
    print('PHYTON-Side compress:' +x.compressToBase64(s))
    print('JS-Side (Already Compressed Base64 LZString):' +jsLzStringCompressToBase64)
    print('-------------------------------------')
    print('Decompress with Phyton from base64: TEST is OK if original uncompressed string results starting from both Phyton-Side and JS_Side already compressed Strings')
    print('From phyton :' + x.decompressFromBase64(x.compressToBase64(s)))
    print('From JS:' + x.decompressFromBase64(jsLzStringCompressToBase64))
    print('-------------------------------------')   
   
    print('Compress with EncodedeUriComponent: TEST is OK if PHYTON-Side string is the same of the JS-Side one')
    print('PHYTON-Side URI compress:' +x.compressToEncodedURIComponent(s))
    print('JS-Side (Already Compressed encoded UriComp LZString)::' + jsLzStringCompressToEncodedeUriComponent)
    print('-------------------------------------')
    print('Decompress from EncodedeUriComponent: TEST is OK if original uncompressed string results starting from both Phyton-Side and JS_Side already compressed Strings')
    print('PHYTON:' + x.decompressFromEncodedURIComponent(x.compressToEncodedURIComponent(s)))
    print('js:' + x.decompressFromEncodedURIComponent(jsLzStringCompressToEncodedeUriComponent))

