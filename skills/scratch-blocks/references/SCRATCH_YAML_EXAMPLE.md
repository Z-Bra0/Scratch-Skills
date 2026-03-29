```scratch-yaml
- name: Sprite1
  variables: {}
  lists:
    - name: list2
      items:
        - "1"
        - "2"
  blocks:
    - - opcode: event_whenflagclicked
      - opcode: control_if_else
        params:
          - opcode: sensing_keypressed
            params: [space]
        blocks:
          - - opcode: motion_movesteps
              params: [10]
          - - opcode: looks_say
              params: [blocked!]
```
