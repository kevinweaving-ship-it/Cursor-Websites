// Boat Puck — GoPro HERO9–13 housing insert envelope (PROVISIONAL)
// Units: millimetres
// Source: camera chassis 71.8 x 50.8 x 33.6 (Clifton/Hypoxic); insert = chassis - margin
// Print envelope_dummy() and drop-fit in ADDIV-001 / Telesin before freezing PCB.

/* [Envelope] */
camera_W = 71.8;
camera_H = 50.8;
camera_D = 33.6;
margin_xy = 1.0;   // mm per side
margin_z  = 1.6;   // mm total depth margin (front+back)

insert_W = camera_W - 2*margin_xy; // 69.8 → round to 70.0 in docs
insert_H = camera_H - 2*margin_xy;
insert_D = camera_D - margin_z;

// Documented design box (slightly rounded)
design_W = 70.0;
design_H = 49.0;
design_D = 32.0;

/* [Keep-outs — estimates; zero or edit after calipers] */
lens_boss_od = 22;
lens_boss_depth = 6;
latch_keep_h = 4;
door_crush_z = 1.5;

$fn = 64;

module camera_proxy() {
  color([0.3,0.55,0.9,0.35])
    cube([camera_W, camera_H, camera_D], center=true);
}

module insert_box(w=design_W, h=design_H, d=design_D) {
  color([0.3,0.75,0.35,0.7])
    cube([w, h, d], center=true);
}

// Print this: solid brick at max insert size
module envelope_dummy() {
  difference() {
    insert_box();
    // chamfer-ish marker notch at "front" (+Y in this file = top; front = -Z)
    translate([0, design_H/2 - 1.5, -design_D/2 + 1])
      cube([8, 3, 2], center=true);
  }
}

// Visual: insert with provisional keep-out voids (not for print unless needed)
module insert_with_keepouts() {
  difference() {
    insert_box();
    // lens boss from front (-Z)
    translate([0, 0, -design_D/2 + lens_boss_depth/2 - 0.01])
      cylinder(h=lens_boss_depth, d=lens_boss_od, center=true);
    // latch strip at top (+Y)
    translate([0, design_H/2 - latch_keep_h/2, 0])
      cube([design_W*0.4, latch_keep_h, design_D], center=true);
    // rear door crush pad
    translate([0, 0, design_D/2 - door_crush_z/2])
      cube([design_W, design_H, door_crush_z], center=true);
  }
}

// Default preview: camera ghost + design insert
camera_proxy();
translate([0, 0, 0]) insert_box();

// Uncomment one for export:
// envelope_dummy();
// insert_with_keepouts();

echo(str("design insert mm: ", design_W, " x ", design_H, " x ", design_D));
echo(str("computed insert mm: ", insert_W, " x ", insert_H, " x ", insert_D));
