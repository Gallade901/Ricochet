"""Add shop, weapon progression, HP and timed phase ability to existing player.
Existing input, aim and projectile graphs are extended in place, never regenerated.
"""
import sys
from pathlib import Path
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
from progression_common import *

player = load(GAME + '/BP_RA_PlayerCharacter')
projectile = load(GAME + '/BP_RA_RicochetProjectile')
hud = load(GAME + '/BP_RA_HUD')
assert 'WeaponDamage' not in B.list_variables(player), 'Already authored; inspect instead of overwriting'
tool = unreal.get_default_object(unreal.UMGToolSet.static_class())
shop = tool.call_method('CreateWidgetBlueprint', args=(BASE, 'WBP_RA_UpgradeShop', unreal.UserWidget.static_class()))
core.ASSETS[shop.get_name()] = shop

# Translucency is an actual material replacement, not just an invisible target flag.
phase = unreal.load_asset(BASE + '/M_RA_Phase')
if not phase:
    phase = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_RA_Phase', BASE, unreal.Material, unreal.MaterialFactoryNew())
    phase.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    color = unreal.MaterialEditingLibrary.create_material_expression(phase, unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', unreal.LinearColor(0.15, 0.7, 1.0, 1))
    alpha = unreal.MaterialEditingLibrary.create_material_expression(phase, unreal.MaterialExpressionConstant)
    alpha.set_editor_property('r', 0.28)
    unreal.MaterialEditingLibrary.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    unreal.MaterialEditingLibrary.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    unreal.MaterialEditingLibrary.recompile_material(phase)
    assert unreal.EditorAssetLibrary.save_loaded_asset(phase, False)

for name, kind, value in [
    ('WeaponDamage', 'float', float(core.cdo(projectile).get_editor_property('Damage'))),
    ('DamageUpgradeLevel', 'int', 0), ('FireUpgradeLevel', 'int', 0),
    ('MaxUpgradeLevel', 'int', 8), ('StealthOwned', 'bool', False),
    ('StealthActive', 'bool', False), ('StealthEndTime', 'float', 0.0),
    ('NextStealthReady', 'float', 0.0), ('StealthDuration', 'float', 5.0),
    ('StealthCooldown', 'float', 30.0), ('ShopOpen', 'bool', False),
    ('MaxPlayerHealth', 'float', 100.0), ('PlayerHealth', 'float', 100.0),
    ('PlayerDead', 'bool', False), ('LastPurchaseSucceeded', 'bool', False)]:
    var(player, name, kind, value)
objvar(player, 'ShopWidget', unreal.UserWidget)
objvar(player, 'PhaseMaterial', unreal.MaterialInterface)
objvar(player, 'OriginalBodyMaterial', unreal.MaterialInterface)
objvar(player, 'OriginalWeaponMaterial', unreal.MaterialInterface)
B.compile_blueprint(player)
core.cdo(player).set_editor_property('PhaseMaterial', phase)

cost = fn(player, 'GetUpgradeCost', [('Choice', 'int')], [('Cost', 'int')])
purchase = fn(player, 'TryPurchaseUpgrade', [('Choice', 'int')])
toggle = fn(player, 'ToggleUpgradeShop')
activate = fn(player, 'TryActivateStealth')
end = fn(player, 'EndStealth')
update = fn(player, 'UpdatePlayerGameplay')
receive = fn(player, 'ReceiveRobotDamage', [('Amount', 'float')])
initialize = fn(player, 'InitializeProgression')
for name in ['RefreshShop', 'BuyDamage', 'BuyRate', 'BuyStealth', 'CloseShop']:
    fn(shop, name)
B.compile_blueprint(player)
B.compile_blueprint(shop)

write(cost, f'''(fn GetUpgradeCost (Choice)
  (if (== Choice 0) (return (+ 5 (* {V(player,'DamageUpgradeLevel')} 5)))
    (elif (== Choice 1) (return (+ 5 (* {V(player,'FireUpgradeLevel')} 5)))
      (elif (== Choice 2) (return 15) (else (return 2147483647))))))''')
write(purchase, f'''(fn TryPurchaseUpgrade (Choice)
  {S(player,'LastPurchaseSucceeded','false')}
  (if (and {V(player,'ShopOpen')} (not {V(player,'PlayerDead')}))
    (bind price {F(player,'GetUpgradeCost',Choice='Choice')})
    (if (and (>= {V(player,'Microchips')} price) (>= Choice 0))
      (if (and (== Choice 0) (< {V(player,'DamageUpgradeLevel')} {V(player,'MaxUpgradeLevel')}))
        {S(player,'Microchips','(- '+V(player,'Microchips')+' price)')}
        {S(player,'DamageUpgradeLevel','(+ '+V(player,'DamageUpgradeLevel')+' 1)')}
        {S(player,'WeaponDamage','(+ '+V(player,'WeaponDamage')+' 10.0)')}
        {S(player,'LastPurchaseSucceeded','true')}
        (elif (and (== Choice 1) (< {V(player,'FireUpgradeLevel')} {V(player,'MaxUpgradeLevel')}))
          {S(player,'Microchips','(- '+V(player,'Microchips')+' price)')}
          {S(player,'FireUpgradeLevel','(+ '+V(player,'FireUpgradeLevel')+' 1)')}
          (bind interval (* {V(player,'FireInterval')} 0.85))
          {S(player,'FireInterval','(select (> interval 0.045) interval 0.045)')}
          {S(player,'LastPurchaseSucceeded','true')}
          (elif (and (== Choice 2) (not {V(player,'StealthOwned')}))
            {S(player,'Microchips','(- '+V(player,'Microchips')+' price)')}
            {S(player,'StealthOwned','true')}
            {S(player,'LastPurchaseSucceeded','true')}))))))''')

write(toggle, f'''(fn ToggleUpgradeShop ()
  (if (not {V(player,'PlayerDead')})
    (bind pc ({N(toggle,'GetPlayerController','Game')}))
    (if {V(player,'ShopOpen')}
      {S(player,'ShopOpen','false')}
      ({N(toggle,'SetGamePaused')} :bPaused false)
      ({N(toggle,'RemovefromParent','Widget')} :self {V(player,'ShopWidget')})
      ({N(toggle,'SetInputModeGameOnly','Input')} :PlayerController pc :bFlushInput true)
      (else
        (bind widget ({N(toggle,'CreateWidget','UserInterface')}
          :Class "{BASE}/WBP_RA_UpgradeShop.WBP_RA_UpgradeShop_C" :OwningPlayer pc))
        {S(player,'ShopWidget','widget')}
        {S(player,'ShopOpen','true')}
        ({N(toggle,'AddtoViewport','UserInterface|Viewport')} :self widget :ZOrder 20)
        ({N(toggle,'SetInputModeUIOnly','Input')} :PlayerController pc :InWidgetToFocus widget :bFlushInput true)
        ({N(toggle,'SetGamePaused')} :bPaused true)))))''')

write(activate, f'''(fn TryActivateStealth ()
  (bind now ({N(activate,'GetGameTimeInSeconds')}))
  (if (and (and {V(player,'StealthOwned')} (not {V(player,'StealthActive')}))
           (and (and (not {V(player,'PlayerDead')}) (not {V(player,'ShopOpen')})) (>= now {V(player,'NextStealthReady')})))
    {S(player,'OriginalBodyMaterial','('+N(activate,'GetMaterial','Rendering|Material')+' :self '+V(player,'BodyVisual')+' :ElementIndex 0)')}
    {S(player,'OriginalWeaponMaterial','('+N(activate,'GetMaterial','Rendering|Material')+' :self '+V(player,'WeaponVisual')+' :ElementIndex 0)')}
    {S(player,'StealthActive','true')}
    {S(player,'StealthEndTime','(+ now '+V(player,'StealthDuration')+')')}
    {S(player,'NextStealthReady','(+ now '+V(player,'StealthCooldown')+')')}
    ({N(activate,'SetMaterial','Rendering|Material')} :self {V(player,'BodyVisual')} :ElementIndex 0 :Material {V(player,'PhaseMaterial')})
    ({N(activate,'SetMaterial','Rendering|Material')} :self {V(player,'WeaponVisual')} :ElementIndex 0 :Material {V(player,'PhaseMaterial')})))''')
write(end, f'''(fn EndStealth ()
  (if {V(player,'StealthActive')}
    {S(player,'StealthActive','false')}
    ({N(end,'SetMaterial','Rendering|Material')} :self {V(player,'BodyVisual')} :ElementIndex 0 :Material {V(player,'OriginalBodyMaterial')})
    ({N(end,'SetMaterial','Rendering|Material')} :self {V(player,'WeaponVisual')} :ElementIndex 0 :Material {V(player,'OriginalWeaponMaterial')})))''')
write(receive, f'''(fn ReceiveRobotDamage (Amount)
  (if (and (and (not {V(player,'PlayerDead')}) (not {V(player,'StealthActive')})) (> Amount 0.0))
    (bind health (- {V(player,'PlayerHealth')} Amount))
    {S(player,'PlayerHealth','(select (> health 0.0) health 0.0)')}
    (if (<= {V(player,'PlayerHealth')} 0.0)
      {S(player,'PlayerDead','true')})))''')
write(initialize, f'''(fn InitializeProgression ()
  {S(player,'PlayerHealth',V(player,'MaxPlayerHealth'))}
  {S(player,'PlayerDead','false')} )''')
pressed = N(update,'WasInputKeyJustPressed')
write(update, f'''(fn UpdatePlayerGameplay ()
  (bind now ({N(update,'GetGameTimeInSeconds')}))
  (bind pc ({N(update,'GetPlayerController','Game')}))
  (if (and {V(player,'StealthActive')} (>= now {V(player,'StealthEndTime')})) {F(player,'EndStealth')})
  (if (not {V(player,'PlayerDead')})
    (if ({pressed} :self pc :Key "(KeyName=Tab)") {F(player,'ToggleUpgradeShop')})
    (if ({pressed} :self pc :Key "(KeyName=E)") {F(player,'TryActivateStealth')})
    (else
      (if ({pressed} :self pc :Key "(KeyName=R)")
        (bind map ({N(update,'GetCurrentLevelName')}))
        ({N(update,'OpenLevel(byName)')} :LevelName map)))))''')

# Build a centered modal panel with real buttons and a changing balance/price display.
def widget(cls, name, parent=None, variable=False):
    info = tool.call_method('AddWidget', args=(shop, cls.static_class(), name, parent, -1))
    if variable: tool.call_method('ToggleWidgetAsVariable',args=(shop, info.widget, True))
    return info

canvas = widget(unreal.CanvasPanel,'ShopCanvas').widget
shade = widget(unreal.Border,'DimBackground',canvas)
shade.widget.set_brush_color(unreal.LinearColor(0,0,0,0.75))
shade.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0), maximum=unreal.Vector2D(1,1)))
shade.slot.set_offsets(unreal.Margin(0,0,0,0))
panel = widget(unreal.Border,'ShopPanel',canvas)
panel.widget.set_brush_color(unreal.LinearColor(0.025,0.045,0.07,1))
panel.widget.set_padding(unreal.Margin(24,18,24,18))
panel.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0.5,0.5), maximum=unreal.Vector2D(0.5,0.5)))
panel.slot.set_alignment(unreal.Vector2D(0.5,0.5))
panel.slot.set_position(unreal.Vector2D(0,0)); panel.slot.set_size(unreal.Vector2D(600,610))
column = widget(unreal.VerticalBox,'ShopColumn',panel.widget).widget
for name,text in [('Title','МАСТЕРСКАЯ ОРУЖИЯ'),('BalanceLabel',''),('DamageLabel',''),('RateLabel',''),('StealthLabel','')]:
    info=widget(unreal.TextBlock,name,column,True)
    info.widget.set_text(text)
    font=info.widget.get_editor_property('font'); font.set_editor_property('size',20)
    info.widget.set_font(font)
    info.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(0.75,0.94,1,1)))
    info.slot.set_padding(unreal.Margin(0,7,0,7))
buttons=[]
for name,text in [('DamageButton','УЛУЧШИТЬ УРОН +10'),('RateButton','ИНТЕРВАЛ МЕЖДУ ВЫСТРЕЛАМИ -15%'),
                  ('StealthButton','КУПИТЬ ПРОЗРАЧНОСТЬ — 15 ПОИНТОВ'),('CloseButton','ПРОДОЛЖИТЬ ИГРУ')]:
    box=widget(unreal.SizeBox,name+'Size',column).widget; box.set_height_override(54)
    info=widget(unreal.Button,name,box,True)
    info.widget.set_background_color(unreal.LinearColor(0.08,0.28,0.38,1))
    text_info=widget(unreal.TextBlock,name+'Text',info.widget)
    text_info.widget.set_text(text)
    font=text_info.widget.get_editor_property('font'); font.set_editor_property('size',17); text_info.widget.set_font(font)
    buttons.append(info.widget)
hint=widget(unreal.TextBlock,'ShopHint',column).widget
hint.set_text('E: прозрачность на 5 с. Перезарядка: 30 с.\nВ мастерской игра приостановлена.')
font=hint.get_editor_property('font'); font.set_editor_property('size',16);hint.set_font(font)
B.compile_blueprint(shop)

refresh=unreal.BlueprintEditorLibrary.find_graph(shop,'RefreshShop')
append=N(refresh,'Append','Utilities|String')
def join(*values):
    result=values[0]
    for value in values[1:]:result=f'({append} {result} {value})'
    return result
cast=core.node(refresh,'CastToBP_RA_PlayerCharacter')
set_text=N(refresh,'SetText(Text)','Widget')
enabled=N(refresh,'SetIsEnabled','Widget')
write(refresh, f'''(fn RefreshShop ()
  (bind player ({cast} :Object ({N(refresh,'GetPlayerCharacter')}))
    (:then
      (bind damagePrice {F(player,'GetUpgradeCost',self='player',Choice='0')})
      (bind ratePrice {F(player,'GetUpgradeCost',self='player',Choice='1')})
      ({set_text} :self {V(shop,'BalanceLabel')} :InText {join('"ПОИНТЫ: "',G(player,'Microchips','player'))})
      ({set_text} :self {V(shop,'DamageLabel')} :InText {join('"Урон: "',G(player,'WeaponDamage','player'),'" | Цена: "','damagePrice')})
      ({set_text} :self {V(shop,'RateLabel')} :InText {join('"Интервал: "',G(player,'FireInterval','player'),'" с | Цена: "','ratePrice')})
      ({set_text} :self {V(shop,'StealthLabel')} :InText (select {G(player,'StealthOwned','player')}
        "Прозрачность куплена. Активация: E" "Прозрачность: 5 секунд без преследования"))
      ({enabled} :self {V(shop,'DamageButton')} :bInIsEnabled
        (and (>= {G(player,'Microchips','player')} damagePrice) (< {G(player,'DamageUpgradeLevel','player')} {G(player,'MaxUpgradeLevel','player')})))
      ({enabled} :self {V(shop,'RateButton')} :bInIsEnabled
        (and (>= {G(player,'Microchips','player')} ratePrice) (< {G(player,'FireUpgradeLevel','player')} {G(player,'MaxUpgradeLevel','player')})))
      ({enabled} :self {V(shop,'StealthButton')} :bInIsEnabled
        (and (>= {G(player,'Microchips','player')} 15) (not {G(player,'StealthOwned','player')}))))
    (:CastFailed)))''')
for name,choice in [('BuyDamage',0),('BuyRate',1),('BuyStealth',2),('CloseShop',None)]:
    g=unreal.BlueprintEditorLibrary.find_graph(shop,name)
    action=F(player,'ToggleUpgradeShop',self='player') if choice is None else F(player,'TryPurchaseUpgrade',self='player',Choice=str(choice))
    write(g,f'''(fn {name} ()
      (bind player ({core.node(g,'CastToBP_RA_PlayerCharacter')} :Object ({N(g,'GetPlayerCharacter')}))
        (:then {action} {F(shop,'RefreshShop')}) (:CastFailed)))''')
B.compile_blueprint(shop)
events=B.get_graph(shop,'EventGraph')
for button,handler in zip(buttons,['BuyDamage','BuyRate','BuyStealth','CloseShop']):
    assert tool.call_method('BindToEventProperty',args=(shop,unreal.Name('OnClicked'),unreal.Name(button.get_name()),unreal.Button.static_class()))
    matches=[n for n in unreal.BlueprintGraphEditor.get_graph_editor(events).list_all_nodes()
             if 'OnClicked' in n.get_node_title().replace(' ', '') and button.get_name() in n.get_node_title()]
    if not matches:
        matches=[n for n in unreal.BlueprintGraphEditor.get_graph_editor(events).list_all_nodes()
                 if 'OnClicked' in n.get_node_title().replace(' ', '') and not pin(n,'then',True).list_connected_pins()]
    assert len(matches)==1,(button.get_name(),[n.get_node_title() for n in matches])
    handler_node=call_node(events,shop,handler); wire(matches[0],'then',handler_node,'execute')
construct=B.create_node(events,N(events,'EventConstruct'),unreal.IntPoint(0,-300))
refresh_node=call_node(events,shop,'RefreshShop'); wire(construct,'then',refresh_node,'execute')

# Extend existing player events and firing chain, preserving every old node.
B.compile_blueprint(player)
pe=B.get_graph(player,'EventGraph'); editor=unreal.BlueprintGraphEditor.get_graph_editor(pe)
tick=editor.find_event_node('ReceiveTick')
old_start=pin(tick,'then',True).list_connected_pins()[0]
sequence=B.create_node(pe,N(pe,'Sequence','Utilities|FlowControl'),unreal.IntPoint(-650,-200))
gate=editor.add_branch_node()
blocked=editor.add_call_function_node('/Script/Engine.KismetMathLibrary:BooleanOR')
dead_get=editor.add_get_member_variable_node('PlayerDead'); shop_get=editor.add_get_member_variable_node('ShopOpen')
wire(dead_get,'PlayerDead',blocked,'A');wire(shop_get,'ShopOpen',blocked,'B');wire(blocked,'ReturnValue',gate,'Condition')
assert pin(tick,'then',True).break_single_pin_link(old_start)
wire(tick,'then',sequence,'execute');wire(sequence,'then_0',gate,'execute')
assert pin(gate,'else',True).try_create_connection(old_start)
up=call_node(pe,player,'UpdatePlayerGameplay');wire(sequence,'then_1',up,'execute')
begin=editor.find_event_node('ReceiveBeginPlay');assert not pin(begin,'then',True).list_connected_pins()
initialize_node=call_node(pe,player,'InitializeProgression');wire(begin,'then',initialize_node,'execute')
fire_graph=B.get_graph(player,'TryFire'); e=unreal.BlueprintGraphEditor.get_graph_editor(fire_graph)
spawn_nodes=[n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_SpawnActorFromClass'];assert len(spawn_nodes)==1
spawn_node=spawn_nodes[0]; old_next=pin(spawn_node,'then',True).list_connected_pins()[0]
valid=e.add_call_function_node('/Script/Engine.KismetSystemLibrary:IsValid'); valid_branch=e.add_branch_node()
damage_set=e.add_set_member_variable_node('Damage',projectile.generated_class().get_path_name())
weapon_get=e.add_get_member_variable_node('WeaponDamage')
wire(spawn_node,'ReturnValue',valid,'Object');wire(valid,'ReturnValue',valid_branch,'Condition')
assert pin(spawn_node,'then',True).break_single_pin_link(old_next)
wire(spawn_node,'then',valid_branch,'execute');wire(valid_branch,'then',damage_set,'execute')
wire(spawn_node,'ReturnValue',damage_set,'self');wire(weapon_get,'WeaponDamage',damage_set,'Damage')
assert pin(damage_set,'then',True).try_create_connection(old_next)
assert pin(valid_branch,'else',True).try_create_connection(old_next)

# New HUD function, original HUD graph is preserved via an event sequence.
render=fn(hud,'DrawProgressionStatus')
B.compile_blueprint(hud)
draw=N(render,'DrawText','HUD');cat=core.node(render,'CastToBP_RA_PlayerCharacter')
write(render,f'''(fn DrawProgressionStatus ()
  (bind player ({cat} :Object ({N(render,'GetPlayerCharacter')}))
    (:then
      ({draw} :Text {join('"HP: "',G(player,'PlayerHealth','player'))} :ScreenX 25.0 :ScreenY 105.0 :Scale 1.6 :TextColor "(R=0.3,G=1.0,B=0.4,A=1.0)")
      ({draw} :Text "Tab: мастерская | E: прозрачность" :ScreenX 25.0 :ScreenY 140.0 :Scale 1.2)
      (if {G(player,'StealthOwned','player')}
        (bind remaining (- {G(player,'NextStealthReady','player')} ({N(render,'GetGameTimeInSeconds')})))
        ({draw} :Text (select {G(player,'StealthActive','player')} "ПРОЗРАЧНОСТЬ АКТИВНА"
          (select (<= remaining 0.0) "Прозрачность готова: E" {join('"Перезарядка: "','('+N(render,'Ceil','Math|Float')+' remaining)','" с"')}))
          :ScreenX 25.0 :ScreenY 175.0 :Scale 1.3 :TextColor "(R=0.2,G=0.8,B=1.0,A=1.0)"))
      (if {G(player,'PlayerDead','player')}
        ({draw} :Text "ВЫ УНИЧТОЖЕНЫ. R: перезапуск" :ScreenX 25.0 :ScreenY 220.0 :Scale 2.0 :TextColor "(R=1.0,G=0.2,B=0.15,A=1.0)")))
    (:CastFailed)))''')
he=B.get_graph(hud,'EventGraph');e=unreal.BlueprintGraphEditor.get_graph_editor(he)
event=e.find_event_node('ReceiveDrawHUD');old=pin(event,'then',True).list_connected_pins()[0]
sequence=B.create_node(he,N(he,'Sequence','Utilities|FlowControl'),unreal.IntPoint(-500,-300))
assert pin(event,'then',True).break_single_pin_link(old)
wire(event,'then',sequence,'execute');assert pin(sequence,'then_0',True).try_create_connection(old)
render_node=call_node(he,hud,'DrawProgressionStatus');wire(sequence,'then_1',render_node,'execute')
core.cdo(shop).set_editor_property('is_focusable',True)
finish([player,shop,hud],'player_shop_build')
unreal.log('PLAYER_SHOP_PROGRESSION_VERIFIED')
