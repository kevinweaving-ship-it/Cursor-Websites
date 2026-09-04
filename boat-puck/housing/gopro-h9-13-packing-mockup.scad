// Boat Puck — H9–13 cavity packing mockups
// Units: mm.  +Z toward backdoor; −Z toward lens/GPS.
// Open in OpenSCAD; set show = "puck" | "screen" | "both"

cam_W = 71.8;
cam_H = 50.8;
cam_D = 33.6;
lens_OD = 33.0;
lens_protrusion = 5.5;
$fn = 48;

/* [Which insert] */
show = "both"; // ["puck", "screen", "both"]

module camera_body_behind_lens() {
  d = cam_D - lens_protrusion;
  translate([0, 0, lens_protrusion / 2])
    cube([cam_W, cam_H, d], center = true);
}

module lens_boss() {
  translate([0, 0, -cam_D / 2 + lens_protrusion / 2])
    cylinder(h = lens_protrusion, d = lens_OD, center = true);
}

module lipo(w, h, t) {
  color([0.15, 0.15, 0.18]) cube([w, h, t], center = true);
}

module pcb(w, h, t) {
  color([0.1, 0.45, 0.2]) cube([w, h, t], center = true);
}

module module_chip(w, h, t) {
  color([0.2, 0.2, 0.25]) cube([w, h, t], center = true);
}

module lcd_panel(w, h, t) {
  color([0.05, 0.35, 0.55]) cube([w, h, t], center = true);
}

module lcd_aa(w, h, t) {
  color([0.15, 0.75, 0.95, 0.85]) cube([w, h, t], center = true);
}

module puck_insert() {
  color([0.5, 0.7, 0.95, 0.12]) camera_body_behind_lens();
  color([0.95, 0.55, 0.15, 0.25]) lens_boss();

  translate([0, 0, -cam_D / 2 + 2.5])
    color([0.85, 0.85, 0.9]) cylinder(h = 4.0, d = 25, center = true);

  translate([0, 0, -cam_D / 2 + lens_protrusion + 2.0])
    pcb(28, 28, 3.0);

  translate([-20, 12, -2]) module_chip(18, 16, 3.0);
  translate([-20, -12, -2]) module_chip(12, 12, 2.0);
  translate([18, 10, -2]) module_chip(20, 18, 3.0);

  translate([0, 0, 8]) lipo(60, 40, 8);
  translate([0, 0, 2.5]) pcb(65, 45, 1.6);
}

module screen_insert() {
  color([0.5, 0.7, 0.95, 0.12]) camera_body_behind_lens();
  color([0.95, 0.55, 0.15, 0.15]) lens_boss();

  translate([0, 0, cam_D / 2 - 2.0]) lcd_panel(58, 35, 2.5);
  translate([0, 0, cam_D / 2 - 0.6]) lcd_aa(40.8, 30.6, 0.8);

  translate([18, -12, 0]) module_chip(18, 16, 3.0);
  translate([-8, 0, -4]) lipo(45, 30, 6);
  translate([0, 0, 4]) pcb(60, 40, 1.6);
}

module cavity_wireframe() {
  color([0.2, 0.2, 0.2, 0.35])
    difference() {
      cube([cam_W + 0.01, cam_H + 0.01, cam_D + 0.01], center = true);
      cube([cam_W - 0.8, cam_H - 0.8, cam_D + 1], center = true);
    }
}

if (show == "puck" || show == "both") {
  translate(show == "both" ? [-45, 0, 0] : [0, 0, 0]) {
    cavity_wireframe();
    puck_insert();
  }
}

if (show == "screen" || show == "both") {
  translate(show == "both" ? [45, 0, 0] : [0, 0, 0]) {
    cavity_wireframe();
    screen_insert();
  }
}

echo("PUCK: GPS Ø25x4 + GNSS 28x28x3 + LoRa/IMU/MCU + LiPo 60x40x8");
echo("SCREEN: LCD 58x35 + AA 40.8x30.6 + MCU + LiPo 45x30x6");
echo(str("CAVITY ", cam_W, "x", cam_H, "x", cam_D));
